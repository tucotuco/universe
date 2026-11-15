"""HTTP and native-boundary tests for the generated Arena browser shell."""

import json
import io
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from action import Action
from activities import DelayAction, ThrowAction
from melee_defense import MeleeDefense
from arena_web import ArenaSession, make_handler
from atomic_publication import RNGCursor
from attention_intent import accept_spot_attention
from arena_hex_map import HexAddress
from spatial.state import CartesianPosition
from hex_facing import nearest_facing
from measured_values import truncate_position


class TestGeneratedArenaBrowser(unittest.TestCase):
    def setUp(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)

    def request(self, path, payload=None, headers=None):
        handler_type = make_handler(self.session)
        handler = object.__new__(handler_type)
        handler.path = path
        handler.server = type("FakeServer", (), {"server_port": 8000})()
        handler.wfile = io.BytesIO()
        handler.headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            handler.rfile = io.BytesIO(body)
            handler.headers["Content-Length"] = str(len(body))
            handler.headers.setdefault("Content-Type", "application/json")
        result = {}
        handler._send = lambda status, body, content_type="application/json; charset=utf-8": result.update(
            status=status, body=body, content_type=content_type)
        (handler.do_GET if payload is None else handler.do_POST)()
        body = result["body"]
        if result["content_type"].startswith("application/json"):
            body = json.loads(json.dumps(body) if type(body) is not str else body)
        return result["status"], body

    def test_authored_movement_http_route_triggers_incidental_visual_discovery(self):
        """Committed movement to clear sight updates both native observers."""
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 73111,
                                             default_equipment_mode="equipped")
        self.assertEqual(self.request("/api/generated/profile", {"profile_id": "none"})[0], 200)
        status, initial = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "5", "height_cells": "5",
            "root_seed": "73111", "opponent_strategy": "none",
            "authored_scenario": "arena-spot-demo"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, hidden = (row.native.being for row in candidate.participants)
        self.assertNotIn(hidden.name, json.dumps(initial))

        status, planned = self.request("/api/generated/destination", {
            "column": 2, "row": 0, "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        self.assertNotIn(hidden.id, json.dumps(planned))
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(candidate.encounter.time, 1)
        self.assertEqual(player.get_position().as_tuple(), (2.2, 0.5, 0.0))
        path = candidate.encounter.line_of_sight(player.id, hidden.id)
        self.assertEqual(path.status, "clear", path.unmodeled_entity_ids)
        revealed = self.session.public_view()
        self.assertIn(hidden.name, json.dumps(revealed["entities"]))
        self.assertIn(hidden.id, candidate.encounter.aware_beings(player.id))
        self.assertIn(player.id, candidate.encounter.aware_beings(hidden.id))
        self.assertEqual(self.request("/api/generated/stop", {})[0], 200)
        self.assertFalse(revealed["spot_available"])
        self.assertFalse(any(getattr(event, "event_type", None) in ("spot", "search", "listen")
            for event in candidate.universe.event_history.values()))

    def test_authored_search_and_listen_http_controls_preserve_target_privacy(self):
        for sense, authored_fact in (('search', 'arena_search_accessible'),
                                     ('listen', 'arena_audible')):
            with self.subTest(sense=sense):
                self.session = GeneratedArenaSession(root_seed_factory=lambda: 73111,
                    default_equipment_mode='equipped')
                self.request('/api/generated/profile', {'profile_id': 'none'})
                status, initial = self.request('/api/generated/generate', {
                    'starting_experience': '10000', 'width_cells': '5', 'height_cells': '5',
                    'root_seed': '73111', 'opponent_strategy': 'none',
                    'authored_scenario': 'arena-spot-demo'})
                self.assertEqual(status, 200)
                candidate = self.session.active_candidate
                actor, target = (row.native.being for row in candidate.participants)
                self.assertTrue(target.current.tags[authored_fact])
                self.assertNotIn(target.id, json.dumps(initial))
                self.assertNotIn(target.name, json.dumps(initial))
                self.request('/api/generated/run', {})
                self.request('/api/generated/advance', {'seconds': 1})
                before = json.dumps(self.session.public_view())
                self.assertNotIn(target.id, before)
                self.assertNotIn(target.name, before)
                status, accepted = self.request('/api/generated/' + sense, {'sense': sense})
                self.assertEqual(status, 200)
                self.assertEqual(accepted['discovery_actions'][sense]['status'], 'executing')
                self.assertNotIn(target.id, json.dumps(accepted))
                self.assertNotIn(target.name, json.dumps(accepted))
                for _ in range(6):
                    status, result = self.request('/api/generated/advance', {'seconds': 1})
                    self.assertEqual(status, 200, result)
                self.assertEqual(result['discovery_actions'][sense]['outcome'], 'success')
                self.assertIn(target.name, json.dumps(result['entities']))
                learned = next(row for row in result['entities'] if row['name'] == target.name)
                self.assertIsNone(learned['position_meters'])
                self.assertTrue(learned['currently_observable'])
                self.assertIn(target.id, candidate.encounter.aware_beings(actor.id))
                self.assertNotIn(actor.id, candidate.encounter.aware_beings(target.id))
                self.assertFalse(result['spot_available'])
                self.assertFalse(result['search_available'])
                self.assertFalse(result['listen_available'])
                from examples.arena_web import _GENERATED_PAGE
                self.assertIn("e.currently_observable?' · currently evidenced':' · last known'",
                              _GENERATED_PAGE)
                self.assertNotIn("e.currently_observable?' · visible now'", _GENERATED_PAGE)

    def test_search_and_listen_require_authored_source_facts_without_identity_leaks(self):
        for sense, premise in (('search', 'arena_search_accessible'),
                               ('listen', 'arena_audible')):
            with self.subTest(sense=sense):
                self.session = GeneratedArenaSession(root_seed_factory=lambda: 73111,
                    default_equipment_mode='equipped')
                self.request('/api/generated/profile', {'profile_id': 'none'})
                status, initial = self.request('/api/generated/generate', {
                    'starting_experience': '10000', 'width_cells': '5', 'height_cells': '5',
                    'root_seed': '73111', 'opponent_strategy': 'none',
                    'authored_scenario': 'arena-spot-demo'})
                self.assertEqual(status, 200)
                candidate = self.session.active_candidate
                actor, target = (row.native.being for row in candidate.participants)
                target.current.tags[premise] = False
                self.request('/api/generated/run', {})
                self.request('/api/generated/advance', {'seconds': 1})
                before = (candidate.encounter.time, set(candidate.universe.event_history),
                          self.session._rng_cursor.state)
                status, refused = self.request('/api/generated/' + sense, {'sense': sense})
                self.assertEqual(status, 409)
                self.assertNotIn(target.id, json.dumps(refused))
                self.assertNotIn(target.name, json.dumps(refused))
                self.assertEqual(before, (candidate.encounter.time,
                    set(candidate.universe.event_history), self.session._rng_cursor.state))
                self.assertNotIn(target.id, candidate.encounter.aware_beings(actor.id))

    def raw_request(self, path, raw, content_type="application/octet-stream"):
        handler_type = make_handler(self.session)
        handler = object.__new__(handler_type)
        handler.path = path
        handler.server = type("FakeServer", (), {"server_port": 8000})()
        handler.wfile = io.BytesIO()
        handler.headers = {"Content-Length": str(len(raw)), "Content-Type": content_type}
        handler.rfile = io.BytesIO(raw)
        result = {}
        handler._send = lambda status, body, content_type="application/json; charset=utf-8": result.update(
            status=status, body=body, content_type=content_type)
        handler.do_POST()
        body = result["body"]
        if result["content_type"].startswith("application/json"):
            body = json.loads(json.dumps(body) if type(body) is not str else body)
        return result["status"], body

    def test_generated_arena_action_program_declares_targeted_throw_by_opaque_handles(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 5051)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        encounter, universe = candidate.encounter, candidate.universe
        projectile_id = universe.make_object_for_being(player.id, "Rock", "Scenario Rock")
        encounter.add_object(projectile_id)
        encounter.activate_arena_for_player_action(player.id,
            DelayAction(encounter, player.id, 0, encounter.time),
            rng_owner=self.session._rng_cursor)
        encounter.step(1)
        view = self.session.public_view()
        target_row = next(row for row in view["entities"]
                          if row["category"] == "being" and row["name"].startswith(target.name))
        projectile_row = next(row for row in view["character"]["inventory"]["items"]
                              if row["name"] == "Scenario Rock")
        inspected = self.session.inspect_entity({"handle": target_row["handle"]})
        throw_row = next(row for row in inspected["action_catalog"]["entries"]
                         if row["name"] == "throw")
        self.assertEqual(throw_row["status"], "available")
        self.assertEqual(throw_row["target"]["handle"], target_row["handle"])
        self.assertEqual(throw_row["projectiles"][0]["handle"], projectile_row["handle"])
        status, result = self.request("/api/generated/action-program", {"components": [{
            "kind": "throw", "handle": target_row["handle"],
            "projectile_handle": projectile_row["handle"]}]})
        self.assertEqual(status, 200, result)
        action = next(member.action for record in encounter._choice_book._choices.values()
                      for member in record.members if type(member.action) is ThrowAction)
        self.assertIs(type(action), ThrowAction)
        self.assertEqual(action.target_id, target.id)
        self.assertEqual(action.instrument_id, projectile_id)
        self.assertNotIn(target.id, json.dumps(result))
        self.assertNotIn(projectile_id, json.dumps(result))
        encounter.step(4)
        flight = universe.get_object_by_id(projectile_id).__dict__["_projectile_flight"]
        self.assertEqual(action.resolution.outcome, "released")
        self.assertEqual(flight.target_id, target.id)
        self.assertLess(math.dist(flight.landing_position.as_tuple(),
                                  target.get_position().as_tuple()), 1e-6)
        self.assertAlmostEqual(flight.landing_position.x, target.get_position().x)
        self.assertAlmostEqual(flight.landing_position.y, target.get_position().y)
        hp_before_impact = target.current.hit_points
        encounter.step(1)
        flight = universe.get_object_by_id(projectile_id).__dict__["_projectile_flight"]
        self.assertIn(flight.impact_outcome, ("hit", "miss"))
        self.assertEqual(flight.impact_outcome, "hit")
        if flight.impact_outcome == "hit":
            self.assertLess(target.current.hit_points, hp_before_impact)
        else:
            self.assertEqual(target.current.hit_points, hp_before_impact)
            state = universe.get_object_by_id(projectile_id).__dict__["_atomic_projectile_history"][-1]
            self.assertIn(state.miss_direction, range(1, 9))
        impact_view = self.session.public_view()
        observed_projectile = next(row for row in impact_view["projectiles"]
            if row["handle"] == projectile_row["handle"])
        self.assertEqual(observed_projectile["outcome"],
                         flight.impact_outcome)

    def test_generated_arena_targeted_throw_miss_records_direction_without_destination(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 5051)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        encounter, universe = candidate.encounter, candidate.universe
        projectile_id = universe.make_object_for_being(player.id, "Rock", "Scenario Rock")
        encounter.add_object(projectile_id)
        encounter.activate_arena_for_player_action(player.id,
            DelayAction(encounter, player.id, 0, encounter.time),
            rng_owner=self.session._rng_cursor)
        encounter.step(1)
        self.session._rng_cursor.state = random.Random(165).getstate()
        view = self.session.public_view()
        target_row = next(row for row in view["entities"]
            if row["category"] == "being" and row["name"].startswith(target.name))
        projectile_row = next(row for row in view["character"]["inventory"]["items"]
            if row["name"] == "Scenario Rock")
        status, _ = self.request("/api/generated/action-program", {"components": [{
            "kind": "throw", "handle": target_row["handle"],
            "projectile_handle": projectile_row["handle"]}]})
        self.assertEqual(status, 200)
        encounter.step(5)
        object_data = universe.get_object_by_id(projectile_id).__dict__
        flight = object_data["_projectile_flight"]
        state = object_data["_atomic_projectile_history"][-1]
        self.assertEqual(flight.impact_outcome, "miss")
        self.assertIn(flight.miss_direction, range(1, 9))
        self.assertEqual(state.miss_direction, flight.miss_direction)
        self.assertEqual(state.impact_damage, 0)
        self.assertNotEqual(state.position, flight.landing_position)
        player_projectile = next(row for row in self.session.public_view()["projectiles"]
            if row["handle"] == projectile_row["handle"])
        self.assertEqual(player_projectile["status"], "miss_unresolved")
        self.assertEqual(player_projectile["miss_direction"], flight.miss_direction)

    def test_generated_arena_declares_a_held_dagger_throw_by_opaque_handles(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 5051)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        encounter, universe = candidate.encounter, candidate.universe
        weapon_id = universe.make_weapon_for_being(player.id, "Dagger", "Scenario Dagger")
        player.set_body_part_holds_object("right hand", weapon_id)
        encounter.add_object(weapon_id)
        encounter.activate_arena_for_player_action(player.id,
            DelayAction(encounter, player.id, 0, encounter.time),
            rng_owner=self.session._rng_cursor)
        encounter.step(1)
        view = self.session.public_view()
        target_row = next(row for row in view["entities"]
            if row["category"] == "being" and row["name"].startswith(target.name))
        weapon_row = next(row for row in view["character"]["inventory"]["items"]
            if row["name"] == "Scenario Dagger")
        self.assertIn("readied in right hand", weapon_row["status"])
        status, result = self.request("/api/generated/action-program", {"components": [{
            "kind": "throw", "handle": target_row["handle"],
            "projectile_handle": weapon_row["handle"]}]})
        self.assertEqual(status, 200, result)
        action = next(member.action for record in encounter._choice_book._choices.values()
            for member in record.members if type(member.action) is ThrowAction)
        self.assertEqual(action.instrument_id, weapon_id)
        self.assertNotIn(weapon_id, json.dumps(result))

    def test_generated_arena_offers_thrown_coup_de_grace_for_eligible_aware_target(self):
        from dataclasses import replace
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 5051)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        encounter, universe = candidate.encounter, candidate.universe
        player.set_position(CartesianPosition(1.0, 1.0, 0.0))
        target.set_position(CartesianPosition(1.5, 1.0, 0.0))
        target.current.hit_points = 0
        ledger = player._arena_perception_ledger
        evidence = replace(ledger._current[target.id], position=target.get_position())
        ledger._current[target.id] = evidence
        ledger._history = [evidence if row.entity_id == target.id else row
                           for row in ledger._history]
        weapon_id = universe.make_weapon_for_being(player.id, "Dagger", "Coup Dagger")
        player.set_body_part_holds_object("right hand", weapon_id)
        encounter.add_object(weapon_id)
        encounter.activate_arena_for_player_action(player.id,
            DelayAction(encounter, player.id, 0, encounter.time),
            rng_owner=self.session._rng_cursor)
        encounter.step(1)
        view = self.session.public_view()
        target_row = next(row for row in view["entities"]
            if row["category"] == "being" and row["name"].startswith(target.name))
        weapon_row = next(row for row in view["character"]["inventory"]["items"]
            if row["name"] == "Coup Dagger")
        inspected = self.session.inspect_entity({"handle": target_row["handle"]})
        throw_row = next(row for row in inspected["action_catalog"]["entries"]
            if row["name"] == "throw")
        deflect_row = next(row for row in inspected["action_catalog"]["entries"]
            if row["name"].casefold().startswith("deflect"))
        shoot_row = next(row for row in inspected["action_catalog"]["entries"]
            if row["name"].casefold().startswith("shoot"))
        self.assertIn("throughout its complete trajectory", deflect_row["reason"])
        self.assertIn("no arrow", shoot_row["reason"])
        time_before_deflect = encounter.time
        rng_before_deflect = self.session._rng_cursor.state
        pending_before_deflect = tuple(encounter.pending_action_list)
        status, refusal = self.request("/api/generated/action-program", {"components": [{
            "kind": "deflect", "handle": target_row["handle"]}]})
        self.assertEqual(status, 409)
        self.assertIn("no committed evidence of awareness", refusal["error"])
        self.assertEqual(encounter.time, time_before_deflect)
        self.assertEqual(tuple(encounter.pending_action_list), pending_before_deflect)
        self.assertEqual(self.session._rng_cursor.state, rng_before_deflect)
        status, refusal = self.request("/api/generated/action-program", {"components": [{
            "kind": "shoot", "handle": target_row["handle"]}]})
        self.assertEqual(status, 409)
        self.assertIn("do not define arrow velocity/flight time", refusal["error"])
        self.assertEqual(encounter.time, time_before_deflect)
        self.assertEqual(tuple(encounter.pending_action_list), pending_before_deflect)
        self.assertEqual(self.session._rng_cursor.state, rng_before_deflect)
        dagger_option = next(row for row in throw_row["projectiles"]
            if row["handle"] == weapon_row["handle"])
        self.assertTrue(dagger_option["coup_de_grace"])
        status, result = self.request("/api/generated/action-program", {"components": [{
            "kind": "throw", "handle": target_row["handle"],
            "projectile_handle": weapon_row["handle"], "coup_de_grace": True}]})
        self.assertEqual(status, 200, result)
        action = next(member.action for record in encounter._choice_book._choices.values()
            for member in record.members if type(member.action) is ThrowAction)
        self.assertTrue(action.coup_de_grace)


    def test_general_action_program_http_accepts_sequential_and_validated_overlap(self):
        from dataclasses import replace
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261116,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("Compose an ordered native Action program", page)
        self.assertIn("/api/generated/action-program", page)
        self.assertIn("action.name==='Cancel Action program'", page)
        self.assertIn("button.addEventListener('click',abortMultipleAction)", page)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        player.set_position(CartesianPosition(1.0, 1.0, 0))
        target.set_position(CartesianPosition(1.1, 1.0, 0))
        target.set_hex_facing(nearest_facing((player.get_position().x-target.get_position().x,
            player.get_position().y-target.get_position().y,0)))
        evidence = replace(player._arena_perception_ledger._current[target.id],
                           position=target.get_position())
        player._arena_perception_ledger._current[target.id] = evidence
        player._arena_perception_ledger._history = [evidence if row.entity_id == target.id else row
            for row in player._arena_perception_ledger._history]
        encounter.mark_aware(player.id, target.id)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        handle = self.session._view_handles[target.id]
        before_rng = self.session._rng_cursor.state
        overlapping = {"components": [
            {"kind": "touch", "handle": handle, "priority_penalty": 0},
            {"kind": "touch", "handle": handle, "priority_penalty": 3}]}
        status, refusal = self.request("/api/generated/action-program", overlapping)
        self.assertEqual(status, 409)
        self.assertIn("Multi-action skill", refusal["error"])
        self.assertEqual(self.session._rng_cursor.state, before_rng)
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "multi-action", 1)
        sequential = {"components": [
            {"kind": "touch", "handle": handle, "start_offset_seconds": 0,
             "strategy": {"attack": 0, "defense": 0, "timing": 0, "extra_damage": 0}},
            {"kind": "touch", "handle": handle, "start_offset_seconds": 1}]}
        status, accepted = self.request("/api/generated/action-program", sequential)
        self.assertEqual(status, 200, accepted)
        record = next(row for row in encounter._choice_book._choices.values()
                      if len(row.members) == 2 and all(m.action.event_type == "touch" for m in row.members))
        self.assertEqual(tuple((m.action.start_time, m.action.end_time, m.priority_penalty)
                               for m in record.members), ((0, 1, None), (1, 2, None)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ordered-program.json"
            path.write_bytes(self.session.save_encounter_bytes())
            code = ("import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:3); s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "e=s.active_candidate.encounter; r=next(r for r in e._choice_book._choices.values() if len(r.members)==2); "
                "print(json.dumps({'state':r.view.state,'members':[(m.action.start_time,m.action.end_time,m.priority_penalty) for m in r.members]}))")
            env = dict(os.environ, PYTHONPATH=f"{ROOT / 'src'}:{ROOT / 'examples'}")
            restored = subprocess.run([sys.executable, "-B", "-c", code, str(path)],
                cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        restored_program = json.loads(restored.stdout)
        self.assertEqual(restored_program, {"state": "accepted",
            "members": [[0, 1, None], [1, 2, None]]})
        self.assertEqual(self.request("/api/generated/multiple-actions/abort", {})[0], 200)
        self.assertFalse(any(row.view.id == record.view.id
            for row in encounter._choice_book._choices.values()))

    def test_general_action_program_cancels_running_sequential_members(self):
        from dataclasses import replace
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261118,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        self.assertEqual(self.request("/api/generated/generate", {
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})[0], 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        player.set_position(CartesianPosition(1.0, 1.0, 0))
        target.set_position(CartesianPosition(1.1, 1.0, 0))
        target.set_hex_facing(nearest_facing((player.get_position().x-target.get_position().x,
            player.get_position().y-target.get_position().y,0)))
        evidence = replace(player._arena_perception_ledger._current[target.id],
                           position=target.get_position())
        player._arena_perception_ledger._current[target.id] = evidence
        player._arena_perception_ledger._history = [evidence if row.entity_id == target.id else row
            for row in player._arena_perception_ledger._history]
        encounter.mark_aware(player.id, target.id)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        handle = self.session._view_handles[target.id]
        status, _ = self.request("/api/generated/action-program", {"components": [
            {"kind": "touch", "handle": handle},
            {"kind": "touch", "handle": handle, "start_offset_seconds": 1}]})
        self.assertEqual(status, 200)
        record = next(row for row in encounter._choice_book._choices.values()
                      if len(row.members) == 2 and all(m.action.event_type == "touch" for m in row.members))
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        record = encounter._choice_book._choices[record.view.id]
        self.assertEqual(record.view.state, "executing")
        remaining = [aid for aid in record.view.action_ids if aid in encounter.pending_action_list]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(self.request("/api/generated/multiple-actions/abort", {})[0], 200)
        self.assertFalse(any(aid in encounter.pending_action_list for aid in record.view.action_ids))
        self.assertIn(remaining[0], encounter.cancelled_action_list)

    def test_general_action_program_composes_mixed_duration_touch_and_melee(self):
        from dataclasses import replace
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261117,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "multi-action", 1)
        player.set_ability("dexterity", 12)
        target.set_position(CartesianPosition(player.get_position().x + 0.1,
            player.get_position().y, player.get_position().z))
        target.set_hex_facing(nearest_facing((player.get_position().x-target.get_position().x,
            player.get_position().y-target.get_position().y,0)))
        ledger = player._arena_perception_ledger
        evidence = replace(ledger._current[target.id], position=target.get_position())
        ledger._current[target.id] = evidence
        ledger._history = [evidence if row.entity_id == target.id else row for row in ledger._history]
        encounter.mark_aware(player.id, target.id)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        handle = self.session._view_handles[target.id]
        status, accepted = self.request("/api/generated/action-program", {"components": [
            {"kind": "touch", "handle": handle, "priority_penalty": 0},
            {"kind": "melee", "handle": handle, "motion": "thrust",
             "priority_penalty": 3,
             "strategy": {"attack": 0, "defense": 0, "timing": 1, "extra_damage": 0}}]})
        self.assertEqual(status, 200, accepted)
        record = next(row for row in encounter._choice_book._choices.values()
            if len(row.members) == 2 and any(member.priority_penalty is not None for member in row.members))
        touch, strike = (member.action for member in record.members)
        self.assertEqual((touch.event_type, strike.event_type), ("touch", "thrust"))
        self.assertEqual(touch.start_time, strike.start_time)
        self.assertEqual(touch.end_time-touch.start_time, 1)
        self.assertGreater(strike.end_time-strike.start_time, 1)
        self.assertEqual(strike.strategy.timing, 1)
        self.assertEqual(record.view.state, "accepted")
        projected = self.session._view_unlocked()["action_programs"]
        mixed_program = next(program for program in projected
            if [component["name"] for component in program["components"]]
                == ["Touch", "Thrust"])
        self.assertEqual(mixed_program["status"], "accepted")
        self.assertEqual([component["name"] for component in mixed_program["components"]],
                         ["Touch", "Thrust"])
        self.assertEqual([component["priority_penalty"] for component in mixed_program["components"]],
                         [0, 3])
        self.assertNotIn(touch.id, json.dumps(projected))
        with tempfile.TemporaryDirectory() as directory:
            accepted_path=Path(directory)/"accepted-program.json"
            running_path=Path(directory)/"running-mixed-program.json"
            aborted_path=Path(directory)/"aborted-program.json"
            accepted_path.write_bytes(self.session.save_encounter_bytes())
            env=dict(os.environ,PYTHONPATH=f"{ROOT/'src'}:{ROOT/'examples'}")
            advance_code=("import sys;from arena_browser_session import GeneratedArenaSession;"
                "s=GeneratedArenaSession();s.load_encounter_bytes(open(sys.argv[1],'rb').read());"
                "e=s.active_candidate.encounter;b=e._choice_book;"
                "r=next(r for r in b._choices.values() if len(r.members)==2);"
                "assert r.view.state=='accepted';s.advance_one_second();"
                "r=next(r for r in b._choices.values() if len(r.members)==2);"
                "assert r.view.state=='executing' and len([a for a in r.view.action_ids if a in e.pending_action_list])==1;"
                "open(sys.argv[2],'wb').write(s.save_encounter_bytes());print('fresh-running-mixed')")
            first=subprocess.run([sys.executable,'-B','-c',advance_code,str(accepted_path),str(running_path)],
                cwd=ROOT,env=env,capture_output=True,text=True,check=False,timeout=60)
            self.assertEqual(first.returncode,0,first.stderr);self.assertEqual(first.stdout.strip(),'fresh-running-mixed')
            cancel_code=("import sys;from arena_browser_session import GeneratedArenaSession;"
                "s=GeneratedArenaSession();s.load_encounter_bytes(open(sys.argv[1],'rb').read());"
                "e=s.active_candidate.encounter;r=next(r for r in e._choice_book._choices.values() if len(r.members)==2);"
                "assert r.view.state=='executing';s.cancel_multiple_action({});"
                "open(sys.argv[2],'wb').write(s.save_encounter_bytes());print('fresh-aborted')")
            second=subprocess.run([sys.executable,'-B','-c',cancel_code,str(running_path),str(aborted_path)],
                cwd=ROOT,env=env,capture_output=True,text=True,check=False,timeout=60)
            self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(second.stdout.strip(),'fresh-aborted')
            verify_code=("import json,sys;from arena_browser_session import GeneratedArenaSession;"
                "s=GeneratedArenaSession();s.load_encounter_bytes(open(sys.argv[1],'rb').read());"
                "e=s.active_candidate.encounter;r=next(r for r in e._choice_book._choices.values() if len(r.members)==2);"
                "print(json.dumps({'pending':sorted(e.pending_action_list),'cancelled':sorted(e.cancelled_action_list),"
                "'states':[e._choice_book._states[a] for a in r.view.action_ids]}))")
            final=subprocess.run([sys.executable,'-B','-c',verify_code,str(aborted_path)],
                cwd=ROOT,env=env,capture_output=True,text=True,check=False,timeout=60)
            self.assertEqual(final.returncode,0,final.stderr)
            restored_abort=json.loads(final.stdout)
            self.assertFalse(set(record.view.action_ids).intersection(restored_abort['pending']))
            self.assertEqual(restored_abort['states'],['finished','cancelled'])
        for _ in range(3):
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        cycles = [row for row in encounter._choice_book._choices.values()
                  if row.origin == "multiple-action-cycle"]
        self.assertEqual(len(cycles), 1, [(row.view.state, row.origin,
            [(member.action.event_type, member.action.start_time, member.action.end_time)
             for member in row.members]) for row in encounter._choice_book._choices.values()])
        self.assertEqual(cycles[0].view.first_start, 3)
        self.assertTrue(all(member.action.id not in record.view.action_ids
                            for member in cycles[0].members))
        self.assertIsNotNone(touch.resolution)
        self.assertIsNotNone(strike.resolution)
        self.assertEqual(self.request("/api/generated/multiple-actions/abort", {})[0], 200)
        self.assertTrue(all(action_id not in encounter.pending_action_list
                            for action_id in cycles[0].view.action_ids))

    def test_generate_page_exposes_profile_chooser_upload_and_native_equipment_mode(self):
        status, html = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('id="encounterMode"', html)
        self.assertIn('value="arena_vs_arena">Arena vs Arena (spectator)', html)
        self.assertIn('id="strategyA"', html)
        self.assertIn('id="strategyB"', html)
        self.assertIn("Run up to 10 seconds", html)
        self.assertIn("Pause run", html)
        self.assertIn("hideControlLabel('rate',!manual)", html)
        self.assertIn("hideControlLabel('facingPolicy',!manual)", html)
        self.assertIn("$('encounterMode').value=s.encounter_mode", html)
        self.assertIn('id="groundProfile"', html)
        self.assertIn('id="groundProfileFile"', html)
        self.assertIn('id="equipmentMode"', html)
        self.assertIn("/api/generated/profile-upload", html)
        status, catalog = self.request("/api/generated/profiles")
        self.assertEqual(status, 200)
        self.assertEqual({row["profile_id"] for row in catalog["profiles"]}, {
            "none", "empty", "universe-arena-starter-ground-equipment", "all_swords",
            "one_random_per_weapon_group"})
        profile = (ROOT / "tests" / "fixtures" / "arena" / "empty.json").read_bytes()
        status, uploaded = self.raw_request("/api/generated/profile-upload", profile)
        self.assertEqual(status, 200)
        self.assertTrue(uploaded["selected_profile_id"].startswith("uploaded:"))
        self.assertEqual(uploaded["preview"]["count_per_encounter"], 0)
        self.assertEqual(self.raw_request("/api/generated/profile-upload", profile,
            "text/plain")[0], 409)
        invalid = b'{"format":"wrong","schema_version":1}'
        self.assertEqual(self.raw_request("/api/generated/profile-upload", invalid)[0], 409)

    def test_generate_accepts_reproducible_seed_and_explicit_optional_size_facts(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('id="rootSeed"', page)
        self.assertIn('id="playerSize"', page)
        self.assertIn('id="opponentSize"', page)
        status, view = self.request("/api/generated/generate", {
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "root_seed": "20261107", "size_categories": {"player":"medium","opponent":"medium"}})
        self.assertEqual(status, 200)
        candidate=self.session.active_candidate
        self.assertEqual(candidate.root_seed,20261107)
        self.assertEqual(candidate.participants[0].native.being.size_category,"medium")
        self.assertEqual(candidate.participants[1].native.being.size_category,"medium")
        wire=self.session.save_encounter_bytes()
        restored=GeneratedArenaSession(root_seed_factory=lambda:99)
        restored.load_encounter_bytes(wire)
        self.assertEqual(restored.active_candidate.participants[0].native.being.size_category,"medium")
        self.assertEqual(restored.active_candidate.participants[1].native.being.size_category,"medium")
        bad=self.request("/api/generated/generate", {
            "starting_experience":"1000","width_cells":"5","height_cells":"5",
            "size_categories":{"player":"medium","opponent":"invalid"}})
        self.assertEqual(bad[0],409)

    def test_target_free_dodge_preparation_http_route_and_shipped_browser_controls(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('value="defense_only"', page)
        self.assertIn('Defense only (native Dodge)', page)
        self.assertIn("function submitDodge(handle)", page)
        self.assertIn("/api/generated/dodge", page)
        self.assertIn("actionDodge", page)
        self.assertIn("Retained native Dodge assigned", page)
        self.assertIn("Native Dodge preparation accepted", page)
        self.assertIn("function submitBlock(handle,shieldHandle)", page)
        self.assertIn("/api/generated/block", page)
        self.assertIn("actionBlock", page)
        self.assertIn("function submitYield(handle)", page)
        self.assertIn("/api/generated/parry", page)
        self.assertIn("/api/generated/yield", page)
        self.assertIn("actionYield", page)

        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261107,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        self.assertEqual(generated["opponent_strategy"], "none")
        status, activated = self.request("/api/generated/run", {})
        self.assertEqual(status, 200)
        self.assertTrue(activated["advance_available"])
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        active = activated
        handle = next(row["handle"] for row in active["entities"]
                      if row["category"] == "being")
        status, selected = self.request("/api/generated/inspect", {"handle": handle})
        self.assertEqual(status, 200)
        dodge = next(row for row in selected["action_catalog"]["entries"]
                     if row["name"] == "Dodge")
        self.assertEqual(dodge["status"], "available")
        self.assertNotIn("target_action_id", json.dumps(dodge))
        block = next(row for row in selected["action_catalog"]["entries"]
                     if row["name"] == "Block")
        self.assertEqual(block["status"], "unavailable")
        self.assertIn("No native shield is equipped", block["reason"])
        self.assertEqual(block["shields"], [])
        block_status, refusal = self.request("/api/generated/block", {
            "handle": handle, "shield_handle": "not-an-equipped-shield"})
        self.assertEqual(block_status, 409)
        self.assertIn("actually equipped native shield", refusal["error"])
        yielding = next(row for row in selected["action_catalog"]["entries"]
                        if row["name"] == "Yield")
        self.assertEqual(yielding["status"], "unavailable")
        self.assertIn("destination away from the attacker", yielding["reason"])
        yield_status, refusal = self.request("/api/generated/yield", {"handle": handle})
        self.assertEqual(yield_status, 409)
        self.assertIn("Choose a native destination away", refusal["error"])
        pool = MeleeDefense.dodge_strategy_pool(
            self.session.active_candidate.participants[0].native.being,
            self.session.active_candidate.universe)
        status, accepted = self.request("/api/generated/dodge", {"defense": pool, "timing": 0})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["defense_action"]["status"], "accepted")
        self.assertNotIn("target_action_id", json.dumps(accepted))
        self.assertNotIn("arena-opponent-dodge", json.dumps(accepted))
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        status, ready = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(ready["defense_action"]["status"], "ready")

    def test_target_free_parry_preparation_uses_native_http_session_route(self):
        status, view = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        weapon_id = next(iter(player.armed_with(candidate.universe).values()))
        weapon = candidate.universe.get_object_by_id(weapon_id)
        player.set_weapon_skill_level(candidate.universe.get_weapon_dictionary(),
                                      weapon.original.obj_type, 2)
        weapon_handle = self.session._view_handles[weapon_id]
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        status, accepted = self.request("/api/generated/parry", {
            "weapon_handle": weapon_handle, "motion": "thrust"})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["defense_action"]["status"], "accepted")
        defense = self.session._latest_melee_defense(candidate, player)
        self.assertIsNone(defense.target_action_id)
        self.assertEqual(defense.parry_motion, "thrust")
        self.assertEqual(accepted["defense_action"]["duration_seconds"], max(1, weapon.Tt() - 1))

    def test_generated_multiple_grapple_break_program_uses_native_choice_and_abort(self):
        from action import Action
        from action_evaluation import RandomDraw, _ProvisionalRandom
        from dataclasses import replace
        from physical_contact import active_contact_state

        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261115,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("submitMultipleGrappleBreak", page)
        self.assertIn("/api/generated/multiple-contact", page)
        self.assertIn("Multiple contact action order", page)
        self.assertIn("Multiple contact priority allocation", page)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "5", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        for being in (player, target):
            being.current.body_parts["left hand"] = None
            being.current.body_parts["right hand"] = None
            being.current.skills.skills["improved grapple"] = 3
            being.set_ability("strength", 10)
            being.size_category = "medium"
            being.set_posture("standing")
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "multi-action", 1)
        player.set_position(CartesianPosition(1.0, 1.0, 0))
        target.set_position(CartesianPosition(1.1, 1.0, 0))
        target.set_hex_facing(nearest_facing((player.get_position().x - target.get_position().x,
            player.get_position().y - target.get_position().y, 0)))
        ledger = player._arena_perception_ledger
        evidence = replace(ledger._current[target.id], position=target.get_position())
        ledger._current[target.id] = evidence
        ledger._history = [evidence if row.entity_id == target.id else row
                           for row in ledger._history]
        encounter.mark_aware(target.id, player.id)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        target_handle = self.session._view_handles[target.id]
        self.assertEqual(self.request("/api/generated/touch", {"handle": target_handle})[0], 200)
        touch_player = self.session._player_touch_action(candidate, player)
        touch_target = Action(candidate.universe, encounter.time, encounter.time + 1,
                              "touch", target.id, player.id, None)
        encounter.schedule_action(touch_target)

        touch_values = {touch_player.id: iter((20, 1)), touch_target.id: iter((20, 1))}
        def touch_roll(context, dice):
            value = next(touch_values[context.action_id])
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", touch_roll):
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(touch_player.resolution.outcome, "touched")
        self.assertEqual(touch_target.resolution.outcome, "touched")

        self.assertEqual(self.request("/api/generated/grappling", {
            "action": "grab", "handle": target_handle, "hand": "left hand"})[0], 200)
        grab_target = Action(candidate.universe, encounter.time, encounter.time + 1,
                             "grab", target.id, player.id, None)
        grab_target.touch_action_id = touch_target.id
        grab_target.grab_hand = "left hand"
        encounter.schedule_action(grab_target)
        grab_player = next(member.action for record in encounter._choice_book._choices.values()
                           for member in record.members if member.action.event_type == "grab"
                           and member.action.actor_id == player.id)
        grab_values = {grab_player.id: iter((6, 6, 6, 1, 1, 1)),
                       grab_target.id: iter((6, 6, 6, 1, 1, 1))}
        def grab_roll(context, dice):
            value = next(grab_values[context.action_id])
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", grab_roll):
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(grab_player.resolution.outcome, "success")
        self.assertEqual(grab_target.resolution.outcome, "success")
        self.assertEqual(len(active_contact_state(encounter)[0]), 2)

        status, selected = self.request("/api/generated/inspect", {"handle": target_handle})
        self.assertEqual(status, 200)
        program_row = next(row for row in selected["action_catalog"]["entries"]
                           if row["name"] == "Multiple Grapple + Break hold")
        self.assertEqual(program_row["status"], "available", program_row["reason"])
        choices_before = encounter.choice_state
        rng_before = self.session._rng_cursor.state
        invalid_status, refusal = self.request("/api/generated/multiple-contact", {
            "handle": target_handle, "actions": ["grapple", "break hold"],
            "priorities": [0, 4]})
        self.assertEqual(invalid_status, 409)
        self.assertIn("adopted priorities", refusal["error"])
        self.assertEqual(encounter.choice_state, choices_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)

        status, accepted = self.request("/api/generated/multiple-contact", {
            "handle": target_handle, "actions": ["grapple", "break hold"],
            "priorities": [0, 3]})
        self.assertEqual(status, 200, accepted)
        record = next(row for row in encounter._choice_book._choices.values()
                      if any(member.priority_penalty is not None and
                             member.action.actor_id == player.id for member in row.members))
        self.assertEqual(tuple(member.action.event_type for member in record.members),
                         ("grapple", "break hold"))
        self.assertEqual(tuple(member.priority_penalty for member in record.members), (0, 3))
        grapple, break_hold = (member.action for member in record.members)
        self.assertEqual((grapple.end_time - grapple.start_time,
                          break_hold.end_time - break_hold.start_time), (6, 1))
        program_wire = self.session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            program_path = Path(directory) / "multiple-grapple-break.json"
            program_path.write_bytes(program_wire)
            restore_code = (
                "import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:1); "
                "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "e=s.active_candidate.encounter; "
                "r=next(r for r in e._choice_book._choices.values() "
                "if any(m.priority_penalty is not None for m in r.members)); "
                "print(json.dumps({'time':v['time_seconds'],'state':r.view.state,"
                "'members':[(m.action.event_type,m.priority_penalty) for m in r.members],"
                "'action_ids':list(r.view.action_ids),'pending':sorted(e.pending_action_list)}))")
            restored = subprocess.run([sys.executable, "-B", "-c", restore_code,
                str(program_path)], cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep
                     + os.environ.get("PYTHONPATH", "")},
                check=True, capture_output=True, text=True)
        restored_program = json.loads(restored.stdout)
        self.assertEqual(restored_program["time"], 2)
        self.assertEqual(restored_program["state"], "accepted")
        self.assertEqual(restored_program["members"], [["grapple", 0], ["break hold", 3]])
        self.assertEqual(set(restored_program["action_ids"]), {grapple.id, break_hold.id})
        self.assertEqual(restored_program["pending"], [])
        break_values = iter((6, 6, 6, 1, 1, 1))
        def break_roll(context, dice):
            value = next(break_values)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", break_roll):
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(break_hold.resolution.outcome, "success")
        self.assertIn(grapple.id, encounter.pending_action_list)
        self.assertEqual(self.request("/api/generated/multiple-actions/abort", {})[0], 200)
        self.assertNotIn(grapple.id, encounter.pending_action_list)
        self.assertIn(grapple.id, encounter.cancelled_action_list)
        self.assertEqual(encounter.get_choice(record.view.id).state, "finished")

    def test_player_defender_assigns_block_to_observed_attack(self):
        from dataclasses import replace
        from melee_combat import MeleeStrike, effective_melee_reach_meters

        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261113,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        defender = candidate.participants[0].native.being
        attacker = candidate.participants[1].native.being
        shield_id = candidate.encounter.make_weapon_for_being(
            defender.id, "Small shield", "Test defender shield")
        candidate.encounter.arm_being(defender.id, shield_id, "shield hand")
        candidate.universe.get_object_by_id(shield_id).parent_container_id = defender.id
        shield_handle = "test-only-opaque-shield-handle"
        self.session._view_handles[shield_id] = shield_handle
        attacker_weapon_id = attacker.current.body_parts["right hand"]
        attacker_weapon = candidate.universe.get_object_by_id(attacker_weapon_id)
        attacker.set_position(CartesianPosition(defender.get_position().x + 0.1,
            defender.get_position().y, defender.get_position().z))
        attacker.set_hex_facing(nearest_facing((defender.get_position().x - attacker.get_position().x,
            defender.get_position().y - attacker.get_position().y, 0)))
        ledger = defender._arena_perception_ledger
        evidence = replace(ledger._current[attacker.id], position=attacker.get_position())
        ledger._current[attacker.id] = evidence
        ledger._history = [evidence if row.entity_id == attacker.id else row
                           for row in ledger._history]
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        attacker.strategy.attack = 0
        strike = MeleeStrike(candidate.encounter, attacker.id, defender.id, attacker_weapon_id,
            motion="thrust", reach=effective_melee_reach_meters(attacker.current,
                                                                 attacker_weapon.current))
        candidate.encounter.schedule_action(strike)
        self.assertEqual(strike._status(candidate.encounter)[0], "in_reach")
        for _ in range(2):
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(strike._status(candidate.encounter)[0], "in_reach")
        attacker_handle = self.session._view_handles[attacker.id]
        self.assertEqual(self.request("/api/generated/inspect", {"handle": attacker_handle})[0], 200)
        selected = self.request("/api/generated/inspect", {"handle": attacker_handle})[1]
        block_row = next(row for row in selected["action_catalog"]["entries"]
                         if row["name"] == "Block")
        self.assertEqual(block_row["status"], "available", block_row["reason"])
        self.assertIn(shield_handle, json.dumps(block_row))
        status, accepted = self.request("/api/generated/block", {
            "handle": attacker_handle, "shield_handle": shield_handle})
        self.assertEqual(status, 200, accepted)
        defense = self.session._latest_melee_defense(candidate, defender)
        self.assertEqual(defense.kind, "block")
        self.assertEqual(defense.target_action_id, strike.id)
        while candidate.encounter.time < math.ceil(strike.end_time):
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(defense.resolution.outcome, "blocked")
        self.assertIsNotNone(strike.resolution)

    def test_player_defender_assigns_yield_to_observed_attack(self):
        from dataclasses import replace
        from melee_combat import MeleeStrike, effective_melee_reach_meters
        from strategy import Strategy

        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261114,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        defender = candidate.participants[0].native.being
        attacker = candidate.participants[1].native.being
        attacker_weapon_id = attacker.current.body_parts["right hand"]
        attacker_weapon = candidate.universe.get_object_by_id(attacker_weapon_id)
        attacker.set_position(CartesianPosition(defender.get_position().x + 0.1,
            defender.get_position().y, defender.get_position().z))
        attacker.set_hex_facing(nearest_facing((defender.get_position().x - attacker.get_position().x,
            defender.get_position().y - attacker.get_position().y, 0)))
        ledger = defender._arena_perception_ledger
        evidence = replace(ledger._current[attacker.id], position=attacker.get_position())
        ledger._current[attacker.id] = evidence
        ledger._history = [evidence if row.entity_id == attacker.id else row
                           for row in ledger._history]
        layout = candidate.arena_map.layout
        start_cell = layout.cell_at_position(defender.get_position())
        destinations = [layout.center_position(address, z=defender.get_position().z)
                        for address in layout.addresses() if address != start_cell]
        current_distance = math.dist(defender.get_position().as_tuple(),
                                     attacker.get_position().as_tuple())
        destination = min((point for point in destinations
                           if math.dist(point.as_tuple(), attacker.get_position().as_tuple())
                           > current_distance),
                          key=lambda point: math.dist(point.as_tuple(),
                                                      defender.get_position().as_tuple()))
        destination_cell = layout.cell_at_position(destination)
        status, movement = self.request("/api/generated/destination", {
            "column": destination_cell.column, "row": destination_cell.row,
            "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200, movement)
        attacker.strategy.attack = 0
        strike = MeleeStrike(candidate.encounter, attacker.id, defender.id, attacker_weapon_id,
            motion="thrust", reach=effective_melee_reach_meters(attacker.current,
                attacker_weapon.current), strategy=Strategy(timing=3))
        candidate.encounter.schedule_action(strike)
        self.assertEqual(strike.end_time, 2)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(strike._status(candidate.encounter)[0], "in_reach")
        attacker_handle = self.session._view_handles[attacker.id]
        status, accepted = self.request("/api/generated/yield", {"handle": attacker_handle})
        self.assertEqual(status, 200, accepted)
        defense = self.session._latest_melee_defense(candidate, defender)
        self.assertEqual(defense.kind, "yield")
        self.assertEqual(defense.target_action_id, strike.id)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(defense.resolution.outcome, "yielded")
        self.assertIsNotNone(strike.resolution)

    def test_player_defender_assigns_retained_dodge_to_observed_attack(self):
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from melee_combat import MeleeStrike, effective_melee_reach_meters
        from hex_facing import nearest_facing
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261107,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, _ = self.request("/api/generated/generate", {
            "starting_experience":"10000", "width_cells":"10", "height_cells":"5",
            "equipment_mode":"equipped", "opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate
        player=candidate.participants[0].native.being
        attacker=candidate.participants[1].native.being
        attacker_weapon_id=attacker.current.body_parts['right hand']
        attacker_weapon=candidate.universe.get_object_by_id(attacker_weapon_id)
        from dataclasses import replace
        attacker.set_position(CartesianPosition(player.get_position().x+.1,
            player.get_position().y,player.get_position().z))
        attacker.set_hex_facing(nearest_facing((player.get_position().x-attacker.get_position().x,
            player.get_position().y-attacker.get_position().y,0)))
        ledger=player._arena_perception_ledger
        evidence=replace(ledger._current[attacker.id],position=attacker.get_position())
        ledger._current[attacker.id]=evidence
        ledger._history=[evidence if row.entity_id==attacker.id else row for row in ledger._history]
        self.assertEqual(self.request('/api/generated/run',{})[0],200)
        self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        pool=MeleeDefense.dodge_strategy_pool(player,candidate.universe)
        self.assertEqual(self.request('/api/generated/dodge',{'defense':pool,'timing':0})[0],200)
        self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        retained=self.session._retained_defense(candidate,player,'dodge')
        self.assertIsNotNone(retained)
        attacker.strategy.attack=0
        strike=MeleeStrike(candidate.encounter,attacker.id,player.id,attacker_weapon_id,
            motion='thrust',reach=effective_melee_reach_meters(attacker.current,attacker_weapon.current))
        candidate.encounter.schedule_action(strike)
        self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        self.assertLessEqual(retained.ready_at,strike.end_time,
            f'ready_at={retained.ready_at}, strike_end={strike.end_time}, now={candidate.encounter.time}')
        handle=self.session._view_handles[attacker.id]
        status, response=self.request('/api/generated/dodge',{'handle':handle})
        self.assertEqual(status,200,response)
        defense=next(member.action for choice in candidate.encounter._choice_book._choices.values()
            for member in choice.members if type(member.action) is MeleeDefense
            and member.action.target_action_id==strike.id)
        self.assertEqual(strike._status(candidate.encounter)[0],'in_reach')
        attack_roll=1
        player_hp=player.get_hit_points()
        def scripted(context,dice):
            sides=int(dice.split('d',1)[1].split('+',1)[0])
            value=(20 if context.action_id==defense.id else attack_roll) if dice=='1d20' else sides
            context.trace.append(RandomDraw(context.action_id,dice,
                int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',scripted):
            while candidate.encounter.time < math.ceil(strike.end_time):
                candidate.encounter.step(1)
        self.assertEqual(defense.resolution.outcome,'evaded')
        self.assertEqual(strike.resolution.outcome,'hit self')
        self.assertEqual(player.get_hit_points(),player_hp)

    def test_player_defender_assigns_retained_parry_to_observed_attack(self):
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from melee_combat import MeleeStrike, effective_melee_reach_meters
        from dataclasses import replace
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261108,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, _ = self.request("/api/generated/generate", {
            "starting_experience":"10000", "width_cells":"10", "height_cells":"5",
            "equipment_mode":"equipped", "opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate
        defender=candidate.participants[0].native.being
        attacker=candidate.participants[1].native.being
        defender_weapon_id=defender.current.body_parts['right hand']
        attacker_weapon_id=attacker.current.body_parts['right hand']
        defender_weapon=candidate.universe.get_object_by_id(defender_weapon_id)
        attacker_weapon=candidate.universe.get_object_by_id(attacker_weapon_id)
        defender.set_weapon_skill_level(candidate.universe.get_weapon_dictionary(),
            defender_weapon.current.obj_type, 10)
        attacker.set_position(CartesianPosition(defender.get_position().x+.1,
            defender.get_position().y,defender.get_position().z))
        from hex_facing import nearest_facing
        attacker.set_hex_facing(nearest_facing((defender.get_position().x-attacker.get_position().x,
            defender.get_position().y-attacker.get_position().y,0)))
        ledger=defender._arena_perception_ledger
        evidence=replace(ledger._current[attacker.id],position=attacker.get_position())
        ledger._current[attacker.id]=evidence
        ledger._history=[evidence if row.entity_id==attacker.id else row for row in ledger._history]
        self.assertEqual(self.request('/api/generated/run',{})[0],200)
        self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        weapon_handle=self.session._view_handles[defender_weapon_id]
        self.assertEqual(self.request('/api/generated/parry',{
            'weapon_handle':weapon_handle,'motion':'swing'})[0],200)
        preparation=self.session._latest_melee_defense(candidate,defender)
        self.assertIsNone(preparation.target_action_id)
        preparation_seconds=max(1,defender_weapon.St()-1)
        for _ in range(preparation_seconds):
            self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        self.assertIs(self.session._retained_defense(candidate,defender,'parry',
            defender_weapon_id),preparation)
        attacker.strategy.attack=0
        strike=MeleeStrike(candidate.encounter,attacker.id,defender.id,attacker_weapon_id,
            motion='thrust',reach=effective_melee_reach_meters(attacker.current,attacker_weapon.current))
        candidate.encounter.schedule_action(strike)
        self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        attacker_handle=self.session._view_handles[attacker.id]
        status,response=self.request('/api/generated/parry',{
            'handle':attacker_handle,'weapon_handle':weapon_handle})
        self.assertEqual(status,200,response)
        defense=next(member.action for choice in candidate.encounter._choice_book._choices.values()
            for member in choice.members if type(member.action) is MeleeDefense
            and member.action.target_action_id==strike.id)
        self.assertEqual(defense.prepared_defense_action_id,preparation.id)
        self.assertEqual(defense.parry_motion,'swing')
        def scripted(context,dice):
            value=(1 if context.action_id==strike.id else 20) if dice=='1d20' else int(dice.split('d',1)[1])
            context.trace.append(RandomDraw(context.action_id,dice,
                int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',scripted):
            while candidate.encounter.time < math.ceil(strike.end_time):
                self.assertEqual(self.request('/api/generated/advance',{'seconds':1})[0],200)
        self.assertIn(defense.resolution.outcome,('deflected','failed'))
        self.assertEqual(defense.resolution.defenses[0].kind,'parry')
        self.assertIsNotNone(strike.resolution)

    def test_touch_uses_native_choice_http_route_and_survives_pending_save_load(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("function submitTouch(handle)", page)
        self.assertIn("/api/generated/touch", page)
        self.assertIn("actionTouch", page)
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261107,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        status, activated = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        target_id = self.session.active_candidate.participants[1].native.being.id
        target = next(row for row in activated["entities"]
                      if row["category"] == "being"
                      and self.session._view_handles[target_id] == row["handle"])
        status, selected = self.request("/api/generated/inspect", {"handle": target["handle"]})
        self.assertEqual(status, 200)
        touch = next(row for row in selected["action_catalog"]["entries"]
                     if row["name"] == "touch being")
        self.assertEqual(touch["status"], "available")
        multiple_touch = next(row for row in selected["action_catalog"]["entries"]
                              if row["name"] == "Multiple Touch")
        self.assertEqual(multiple_touch["status"], "unavailable")
        self.assertIn("acquired Multi-action skill", multiple_touch["reason"])
        choices_before = self.session.active_candidate.encounter.choice_state
        rng_before = self.session._rng_cursor.state
        multiple_status, multiple_refusal = self.request("/api/generated/multiple-touch", {
            "handle": target["handle"], "priorities": [0, 3]})
        self.assertEqual(multiple_status, 409)
        self.assertIn("acquired Multi-action skill", multiple_refusal["error"])
        self.assertEqual(self.session.active_candidate.encounter.choice_state, choices_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        rejected_status, rejected = self.request("/api/generated/touch", {
            "handle": "not-a-currently-perceived-being"})
        self.assertEqual(rejected_status, 409)
        self.assertIn("opposing Being", rejected["error"])
        self.assertEqual(self.session.active_candidate.encounter.choice_state, choices_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        status, accepted = self.request("/api/generated/touch", {"handle": target["handle"]})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["touch_action"]["status"], "executing")
        native_touch = self.session._player_touch_action(
            self.session.active_candidate,
            self.session.active_candidate.participants[0].native.being)
        self.assertNotIn(native_touch.id, json.dumps(accepted))
        self.assertNotIn(target_id, json.dumps(accepted))
        rng_before_resolution = self.session._rng_cursor.state
        pending_wire = self.session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "pending-arena.json"
            save_path.write_bytes(pending_wire)
            script = (
                "import base64,json,sys; import tests.test_generated_arena_browser; "
                "from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:2); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "v=s.advance_one_second(); "
                "print(json.dumps({'time_seconds':v['time_seconds'],"
                "'touch_action':v['touch_action'],'position':v['player']['position_meters'],"
                "'rng_state':s._rng_cursor.state,'completed_save':"
                "base64.b64encode(s.save_encounter_bytes()).decode('ascii')}))")
            process = subprocess.run([sys.executable, "-c", script, str(save_path)],
                cwd=ROOT, check=True, capture_output=True, text=True)
            cross_process = json.loads(process.stdout)
        completed = self.session.advance_one_second()
        self.assertEqual(cross_process["time_seconds"], 2)
        self.assertEqual(cross_process["touch_action"], completed["touch_action"])
        self.assertEqual(cross_process["position"], completed["player"]["position_meters"])
        self.assertEqual(cross_process["rng_state"], json.loads(json.dumps(self.session._rng_cursor.state)))
        self.assertEqual(completed["time_seconds"], 2)
        self.assertEqual(completed["touch_action"]["status"], "completed")
        self.assertEqual(completed["touch_action"]["outcome"], "out_of_reach")
        self.assertEqual(self.session._rng_cursor.state, rng_before_resolution)
        completed_wire = __import__("base64").b64decode(cross_process["completed_save"])
        with tempfile.TemporaryDirectory() as directory:
            completed_path = Path(directory) / "completed-arena.json"
            completed_path.write_bytes(completed_wire)
            restore_code = (
                "import base64,json,sys; import tests.test_generated_arena_browser; "
                "from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:3); "
                "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "print(json.dumps({'time_seconds':v['time_seconds'],"
                "'touch_action':v['touch_action'],'position':v['player']['position_meters'],"
                "'rng_state':s._rng_cursor.state}))")
            completed_restore = subprocess.run([sys.executable, "-c", restore_code,
                str(completed_path)], cwd=ROOT, check=True, capture_output=True, text=True)
        restored_result = json.loads(completed_restore.stdout)
        self.assertEqual(restored_result["time_seconds"], 2)
        self.assertEqual(restored_result["touch_action"], completed["touch_action"])
        self.assertEqual(restored_result["position"], completed["player"]["position_meters"])
        self.assertEqual(restored_result["rng_state"], json.loads(json.dumps(self.session._rng_cursor.state)))
        restored = GeneratedArenaSession(root_seed_factory=lambda: 3)
        after_load = restored.load_encounter_bytes(completed_wire)
        self.assertEqual(after_load["touch_action"], completed["touch_action"])
        self.assertEqual(after_load["time_seconds"], 2)

    def test_native_multiple_touch_cycle_survives_live_and_recurring_fresh_process_saves(self):
        """Generated Arena declares, saves, restores, repeats and aborts Multiple actions."""
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("submitMultipleTouch(handle,priorityText)", page)
        self.assertIn("/api/generated/multiple-touch", page)
        self.assertIn("abortMultipleAction()", page)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "5", "height_cells": "5",
            "root_seed": "20261107", "equipment_mode": "unequipped",
            "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        # An explicit native test-world skill input, established before the
        # first committed boundary so the receipt remains closed and portable.
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "multi-action", 1)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        status, activated = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        target_handle = self.session._view_handles[target.id]
        self.assertEqual(self.request("/api/generated/inspect", {"handle": target_handle})[0], 200)
        target_row = next(row for row in self.session.public_view()["action_catalog"]["entries"]
                          if row["name"] == "Multiple Touch")
        self.assertEqual(target_row["status"], "available")
        choices_before = encounter.choice_state
        rng_before = self.session._rng_cursor.state
        invalid_status, invalid = self.request("/api/generated/multiple-touch", {
            "handle": target_handle, "priorities": [0, 4]})
        self.assertEqual(invalid_status, 409)
        self.assertIn("adopted priorities", invalid["error"])
        self.assertEqual(encounter.choice_state, choices_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        status, accepted_view = self.request("/api/generated/multiple-touch", {
            "handle": target_handle, "priorities": [1, 2]})
        self.assertEqual(status, 200)
        self.assertEqual(next(row for row in accepted_view["action_catalog"]["entries"]
                          if row["name"] == "Cancel Action program")["status"], "available")
        accepted = next(record for record in encounter._choice_book._choices.values()
                        if record.view.state == "accepted")
        self.assertEqual(tuple(member.priority_penalty for member in accepted.members), (1, 2))
        first_ids = tuple(accepted.view.action_ids)
        with tempfile.TemporaryDirectory() as directory:
            pending_path = Path(directory) / "live-multiple-touch.json"
            repeated_path = Path(directory) / "repeated-multiple-touch.json"
            pending_path.write_bytes(self.session.save_encounter_bytes())
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = __import__("os").pathsep.join(
                (str(ROOT / "tests"), str(ROOT / "src"), str(ROOT / "examples")))
            advance = (
                "import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:1); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); s.advance_one_second(); "
                "e=s.active_candidate.encounter; b=e._choice_book; "
                "rows=[r for r in b._choices.values() if r.origin=='multiple-action-cycle']; "
                "assert len(rows)==1; r=rows[0]; "
                "assert tuple(m.priority_penalty for m in r.members)==(1,2); "
                "assert not set(r.view.action_ids).intersection(json.loads(sys.argv[2])); "
                "open(sys.argv[3],'wb').write(s.save_encounter_bytes()); "
                "print(json.dumps({'time':e.time,'state':r.view.state,'ids':r.view.action_ids,"
                "'penalties':[m.priority_penalty for m in r.members],"
                "'rng':s._rng_cursor.state}))")
            child = subprocess.run([sys.executable, "-B", "-c", advance,
                str(pending_path), json.dumps(first_ids), str(repeated_path)],
                cwd=ROOT, env=env, check=False, capture_output=True, text=True, timeout=90)
            self.assertEqual(child.returncode, 0, child.stderr)
            continued = json.loads(child.stdout)
            self.assertEqual(continued["time"], 2)
            self.assertEqual(continued["state"], "accepted")
            self.assertEqual(continued["penalties"], [1, 2])

            # Resolve one real program cycle, then abort its queued successor
            # through the shipped actor-scoped HTTP control. No private Choice
            # or Action identity is sent by the browser.
            status, cycled = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            self.assertEqual(cycled["time_seconds"], 2)
            self.assertTrue(any(record.origin == "multiple-action-cycle"
                                for record in encounter._choice_book._choices.values()))
            status, _ = self.request("/api/generated/multiple-actions/abort", {})
            self.assertEqual(status, 200)
            self.assertFalse(any(record.origin == "multiple-action-cycle"
                                 and record.view.state in ("accepted", "executing")
                                 for record in encounter._choice_book._choices.values()))

            verify = (
                "import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:2); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "e=s.active_candidate.encounter; b=e._choice_book; "
                "r=next(r for r in b._choices.values() if r.origin=='multiple-action-cycle'); "
                "print(json.dumps({'time':e.time,'state':r.view.state,"
                "'penalties':[m.priority_penalty for m in r.members],"
                "'rng':s._rng_cursor.state}))")
            restored = subprocess.run([sys.executable, "-B", "-c", verify,
                str(repeated_path)], cwd=ROOT, env=env, check=False,
                capture_output=True, text=True, timeout=90)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(json.loads(restored.stdout), {
                "time": 2, "state": "accepted", "penalties": [1, 2],
                "rng": json.loads(json.dumps(continued["rng"]))})
    def test_grab_selector_http_receipt_and_fresh_process_hold_continuation(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("function submitGrappling(action,handle,hand=null,position=null,exitCell=null)", page)
        self.assertIn("/api/generated/grappling", page)
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 7)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience":"10000","width_cells":"5","height_cells":"5",
            "opponent_strategy":"none"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        opponent = candidate.participants[1].native.being
        # Test-authored contact geometry: two explicitly generated Beings stand
        # 10 cm apart within one Arena hex; this does not define production anatomy.
        from spatial.state import CartesianPosition
        player.current.skills.skills["improved grapple"] = 100
        opponent.current.skills.skills["escape artist"] = 1000
        p = player.get_position()
        opponent.set_position(CartesianPosition(p.x + .1, p.y, p.z))
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        status, state = self.request("/api/generated/advance", {"seconds":1})
        self.assertEqual(status, 200)
        handle = next(row["handle"] for row in state["entities"]
                      if row["category"] == "being")
        status, selected = self.request("/api/generated/inspect", {"handle":handle})
        self.assertEqual(status, 200)
        status, accepted_touch = self.request("/api/generated/touch", {"handle":handle})
        self.assertEqual(status, 200)
        status, touched = self.request("/api/generated/advance", {"seconds":1})
        self.assertEqual(status, 200)
        self.assertEqual(touched["touch_action"]["outcome"], "touched")
        row = next(item for item in touched["action_catalog"]["entries"]
                   if item["name"] == "grab being")
        self.assertEqual(row["status"], "available")
        status, accepted = self.request("/api/generated/grappling", {
            "action":"grab","handle":handle,"hand":"left hand"})
        self.assertEqual(status, 200)
        grab_action = next(member.action for choice in candidate.encounter._choice_book._choices.values()
                           for member in choice.members
                           if type(member.action) is Action and member.action.event_type == "grab")
        self.assertNotIn(grab_action.id, json.dumps(accepted))
        self.assertNotIn(opponent.id, json.dumps(accepted))
        status, grabbed = self.request("/api/generated/advance", {"seconds":1})
        self.assertEqual(status, 200)
        self.assertEqual(grabbed["grappling_action"]["outcome"], "success")
        from physical_contact import active_contact_state
        grip_before = active_contact_state(candidate.encounter)[0]
        self.assertEqual(len(grip_before), 1)
        self.assertEqual(grip_before[0][3], "left hand")
        wire = self.session.save_encounter_bytes()
        # Exercise the shipped browser's explicit, selected-hand Release grip
        # route in an isolated restored copy so the Hold/Grapple continuation
        # below still starts from the original generated Encounter.
        release_session = GeneratedArenaSession(root_seed_factory=lambda: 8)
        release_session.load_encounter_bytes(wire)
        release_session._view_unlocked()
        release_handle = release_session._view_handles[opponent.id]
        release_session.inspect_entity({"handle": release_handle})
        release_entries = release_session._view_unlocked()["action_catalog"]["entries"]
        release_entry = next(item for item in release_entries if item["name"] == "release grip")
        self.assertEqual(release_entry["status"], "available")
        self.assertIn("left hand", release_entry["hands"])
        self.session = release_session
        status, release_response = self.request("/api/generated/grappling", {"action":"release grip",
            "handle":release_handle,"hand":"left hand"})
        self.assertEqual(status, 200)
        self.assertEqual(release_response["grappling_action"]["status"], "executing")
        status, release_result = self.request("/api/generated/advance", {"seconds":1})
        self.assertEqual(status, 200)
        self.assertEqual(release_result["grappling_action"]["outcome"], "success")
        self.assertEqual(active_contact_state(release_session.active_candidate.encounter)[0], ())
        release_wire = release_session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as release_directory:
            release_path = Path(release_directory) / "arena-released.json"
            release_path.write_bytes(release_wire)
            restore_release = (
                "import json,sys; import tests.test_generated_arena_browser; "
                "from arena_browser_session import GeneratedArenaSession; "
                "from physical_contact import active_contact_state; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:10); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "print(json.dumps({'time':s.active_candidate.encounter.time,"
                "'grips':active_contact_state(s.active_candidate.encounter)[0]}))")
            restored_release = subprocess.run([sys.executable,"-c",restore_release,str(release_path)],
                cwd=ROOT,check=True,capture_output=True,text=True)
        self.assertEqual(json.loads(restored_release.stdout), {"time":4,"grips":[]})
        with tempfile.TemporaryDirectory() as directory:
            saved_path = Path(directory) / "arena-grip.json"
            saved_path.write_bytes(wire)
            continuation = (
                "import base64,json,sys; import tests.test_generated_arena_browser; "
                "from arena_browser_session import GeneratedArenaSession; "
                "from physical_contact import active_contact_state; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:99); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "v=None; [ (v:=s.advance_one_second()) for _ in range(6) ]; "
                "print(json.dumps({'time':v['time_seconds'],'action':v['grappling_action'],"
                "'grips':active_contact_state(s.active_candidate.encounter)[0],"
                "'rng':s._rng_cursor.state,'save':base64.b64encode(s.save_encounter_bytes()).decode()}))")
            child = subprocess.run([sys.executable,"-c",continuation,str(saved_path)],
                cwd=ROOT,check=True,capture_output=True,text=True)
        continued = json.loads(child.stdout)
        self.assertEqual(continued["time"], 9)
        self.assertEqual(continued["action"]["outcome"], "success")
        self.assertEqual(continued["grips"][0][0], grip_before[0][0])
        self.assertEqual(continued["grips"][0][5], 15)
        continuation_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, continuation_dir)
        hold_path = continuation_dir / "arena-held.json"
        hold_path.write_bytes(__import__("base64").b64decode(continued["save"]))
        prepare_grapple = (
            "import base64,json,sys; import tests.test_generated_arena_browser; "
            "from arena_browser_session import GeneratedArenaSession; "
            "s=GeneratedArenaSession(root_seed_factory=lambda:101); "
            "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
            "v=s._view_unlocked(); e=next(x for x in v['entities'] if x['category']=='being'); "
            "s.inspect_entity({'handle':e['handle']}); "
            "r=next(x for x in s._view_unlocked()['action_catalog']['entries'] if x['name']=='grapple'); "
            "assert r['status']=='available',r; "
            "s.choose_grappling({'action':'grapple','handle':e['handle']}); "
            "print(base64.b64encode(s.save_encounter_bytes()).decode())")
        pending_grapple = subprocess.run([sys.executable,"-c",prepare_grapple,str(hold_path)],
            cwd=ROOT,check=True,capture_output=True,text=True)
        pending_path = continuation_dir / "arena-grapple-preparation.json"
        pending_path.write_bytes(__import__("base64").b64decode(pending_grapple.stdout))
        resolve_grapple = (
            "import base64,json,sys; import tests.test_generated_arena_browser; "
            "from arena_browser_session import GeneratedArenaSession; "
            "from physical_contact import active_contact_state; "
            "s=GeneratedArenaSession(root_seed_factory=lambda:102); "
            "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
            "[ (v:=s.advance_one_second()) for _ in range(6) ]; "
            "print(json.dumps({'time':v['time_seconds'],'action':v['grappling_action'],"
            "'contact':active_contact_state(s.active_candidate.encounter),"
            "'save':base64.b64encode(s.save_encounter_bytes()).decode()}))")
        resolved_grapple = subprocess.run([sys.executable,"-c",resolve_grapple,str(pending_path)],
            cwd=ROOT,check=False,capture_output=True,text=True)
        self.assertEqual(resolved_grapple.returncode, 0, resolved_grapple.stderr)
        grapple_result = json.loads(resolved_grapple.stdout)
        self.assertEqual(grapple_result["time"],15)
        self.assertEqual(grapple_result["action"]["name"],"Grapple")
        self.assertEqual(grapple_result["action"]["outcome"],"success")
        self.assertEqual(len(grapple_result["contact"][0]),1)
        self.assertEqual(len(grapple_result["contact"][1]),1)
        grapple_path = continuation_dir / "arena-grapple-established.json"
        grapple_path.write_bytes(__import__("base64").b64decode(grapple_result["save"]))
        restored_control = subprocess.run([sys.executable,"-c",
            "import json,sys; import tests.test_generated_arena_browser; "
            "from arena_browser_session import GeneratedArenaSession; "
            "from physical_contact import active_contact_state; "
            "s=GeneratedArenaSession(root_seed_factory=lambda:103);s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
            "g,c=active_contact_state(s.active_candidate.encounter); "
            "print(json.dumps({'time':s.active_candidate.encounter.time,'grips':g,'controls':c}))",
            str(grapple_path)],cwd=ROOT,check=True,capture_output=True,text=True)
        control_result=json.loads(restored_control.stdout)
        self.assertEqual(control_result["time"],15)
        self.assertEqual(control_result["grips"][0][0],continued["grips"][0][0])
        self.assertEqual(len(control_result["controls"]),1)
        continue_to_escape = (
            "import base64,json,sys; import tests.test_generated_arena_browser; "
            "from arena_browser_session import GeneratedArenaSession; from action import Action; "
            "from physical_contact import active_contact_state; "
            "s=GeneratedArenaSession(root_seed_factory=lambda:104); "
            "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
            "c=active_contact_state(s.active_candidate.encounter)[1][0]; "
            "p=s.active_candidate.participants[0].native.being; o=s.active_candidate.participants[1].native.being; "
            "e=Action(s.active_candidate.universe,15,21,'grapple escape',o.id,p.id,None);e.grapple_id=c[0];e.end_time=21; "
            "s.active_candidate.encounter.schedule_action(e); "
            "v=None; [(v:=s.advance_one_second()) for _ in range(5)]; "
            "assert next(x for x in s._view_unlocked()['action_catalog']['entries'] if x['name']=='hold being')['status']=='unavailable'; "
            "print(base64.b64encode(s.save_encounter_bytes()).decode())")
        escape_pending = subprocess.run([sys.executable,"-c",continue_to_escape,str(grapple_path)],
            cwd=ROOT,check=False,capture_output=True,text=True)
        self.assertEqual(escape_pending.returncode,0,escape_pending.stderr)
        escape_path = continuation_dir / "arena-escape-and-hold-pending.json"
        escape_path.write_bytes(__import__("base64").b64decode(escape_pending.stdout))
        settle_escape = (
            "import base64,json,sys; import tests.test_generated_arena_browser; "
            "from arena_browser_session import GeneratedArenaSession; from action import Action; "
            "from physical_contact import active_contact_state; "
            "s=GeneratedArenaSession(root_seed_factory=lambda:105); "
            "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read()); v=s.advance_one_second(); "
            "c=active_contact_state(s.active_candidate.encounter); "
            "e=next(s.active_candidate.universe.get_event_by_id(i) for i in s.active_candidate.encounter.finished_action_list "
            "if type(s.active_candidate.universe.get_event_by_id(i)) is Action and s.active_candidate.universe.get_event_by_id(i).event_type=='grapple escape'); "
            "f=s.active_candidate.encounter.inspect_committed(21).action(e.id); "
            "print(json.dumps({'time':v['time_seconds'],'player_action':v['grappling_action'],"
            "'escape':f.facts.outcome,'grips':c[0],'controls':c[1],"
            "'save':base64.b64encode(s.save_encounter_bytes()).decode()}))")
        settled = subprocess.run([sys.executable,"-c",settle_escape,str(escape_path)],
            cwd=ROOT,check=True,capture_output=True,text=True)
        escaped = json.loads(settled.stdout)
        self.assertEqual(escaped["time"],21)
        self.assertEqual(escaped["player_action"]["name"],"Grapple")
        self.assertEqual(escaped["player_action"]["outcome"],"success")
        self.assertEqual(escaped["escape"],"success")
        self.assertEqual(len(escaped["grips"]),1)
        self.assertEqual(escaped["grips"][0][5],27)
        self.assertEqual(escaped["controls"],[])
        escaped_path=continuation_dir/"arena-after-escape.json"
        escaped_path.write_bytes(__import__("base64").b64decode(escaped["save"]))
        restored_escape=subprocess.run([sys.executable,"-c",
            "import json,sys; import tests.test_generated_arena_browser; "
            "from arena_browser_session import GeneratedArenaSession; from physical_contact import active_contact_state; "
            "s=GeneratedArenaSession(root_seed_factory=lambda:106);s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
            "g,c=active_contact_state(s.active_candidate.encounter);print(json.dumps({'time':s.active_candidate.encounter.time,'grips':g,'controls':c}))",
            str(escaped_path)],cwd=ROOT,check=True,capture_output=True,text=True)
        restored_after_escape=json.loads(restored_escape.stdout)
        self.assertEqual(restored_after_escape["time"],21)
        self.assertEqual(restored_after_escape["grips"][0][0],escaped["grips"][0][0])
        self.assertEqual(restored_after_escape["controls"],[])

    def test_generated_http_contact_grapple_takedown_save_load_without_fixture_mutations(self):
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261100)
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"10000","width_cells":"5","height_cells":"5",
            "root_seed":"20261100","equipment_mode":"unequipped",
            "opponent_strategy":"none",
            "size_categories":{"player":"medium","opponent":"medium"}})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate
        player=candidate.participants[0].native.being
        opponent=candidate.participants[1].native.being
        self.assertIn("left hand",player.current.body_parts)
        self.assertIsNone(player.current.body_parts["left hand"])

        # These are ordinary shipped session routes and an explicit Generate
        # size choice; no skill, position, RNG, or contact state is injected.
        status,_=self.request("/api/generated/destination",{
            "column":0,"row":1,"rate":"walk","facing_policy":"turn"})
        self.assertEqual(status,200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        target=self.session._view_handles[opponent.id]
        self.assertEqual(self.request("/api/generated/inspect",{"handle":target})[0],200)
        self.assertEqual(self.request("/api/generated/touch",{"handle":target})[0],200)
        status,touched=self.request("/api/generated/advance",{"seconds":1})
        self.assertEqual(status,200)
        self.assertEqual(touched["touch_action"]["outcome"],"touched")
        grab_row=next(row for row in touched["action_catalog"]["entries"]
                      if row["name"]=="grab being")
        self.assertEqual(grab_row["status"],"available")
        self.assertEqual(self.request("/api/generated/grappling",{
            "action":"grab","handle":target,"hand":"left hand"})[0],200)
        status,grabbed=self.request("/api/generated/advance",{"seconds":1})
        self.assertEqual(status,200)
        self.assertEqual(grabbed["grappling_action"]["outcome"],"success")
        self.assertTrue(any("left hand" in text and "next maintenance check in 6 s" in text
                            for text in grabbed["contact_status"]))
        self.assertEqual(self.request("/api/generated/grappling",{
            "action":"grapple","handle":target})[0],200)

        with tempfile.TemporaryDirectory() as directory:
            pending=Path(directory)/"generated-pending-grapple.json"
            continued=Path(directory)/"generated-takedown.json"
            pending.write_bytes(self.session.save_encounter_bytes())
            env=dict(__import__("os").environ)
            env["PYTHONPATH"]=__import__("os").pathsep.join(
                (str(ROOT/"tests"),str(ROOT/"src"),str(ROOT/"examples")))
            continue_native=(
                "import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "from physical_contact import active_contact_state; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:1); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); v=None; "
                "[(v:=s.advance_one_second()) for _ in range(6)]; "
                "g=v['grappling_action']; c=s.active_candidate; "
                "h=s._view_handles[c.participants[1].native.being.id]; "
                "s.inspect_entity({'handle':h}); "
                "s.choose_grappling({'action':'takedown','handle':h,'position':'prone'}); "
                "[(v:=s.advance_one_second()) for _ in range(6)]; "
                "open(sys.argv[2],'wb').write(s.save_encounter_bytes()); "
                "print(json.dumps({'time':v['time_seconds'],'grapple':g,'action':v['grappling_action'],"
                "'position':active_contact_state(c.encounter)[1][0][6],"
                "'posture':c.participants[1].native.being.get_posture()}))")
            child=subprocess.run([sys.executable,"-B","-c",continue_native,str(pending),str(continued)],
                cwd=ROOT,env=env,check=False,capture_output=True,text=True,timeout=90)
            self.assertEqual(child.returncode,0,child.stderr)
            result=json.loads(child.stdout)
            self.assertEqual(result["time"],15)
            self.assertEqual((result["grapple"]["name"],result["grapple"]["outcome"]),
                             ("Grapple","success"))
            self.assertEqual((result["action"]["name"],result["action"]["outcome"]),
                             ("Takedown","success"))
            self.assertEqual(result["position"],"advantaged_takedown_top")
            self.assertEqual(result["posture"],"lying")
            verify=(
                "import json,sys; from arena_browser_session import GeneratedArenaSession; "
                "from physical_contact import active_contact_state; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:2); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); c=s.active_candidate; "
                "g,p=active_contact_state(c.encounter); "
                "print(json.dumps({'time':c.encounter.time,'grips':len(g),'controls':p[0][6],"
                "'posture':c.participants[1].native.being.get_posture()}))")
            restored=subprocess.run([sys.executable,"-B","-c",verify,str(continued)],
                cwd=ROOT,env=env,check=False,capture_output=True,text=True,timeout=90)
            self.assertEqual(restored.returncode,0,restored.stderr)
            self.assertEqual(json.loads(restored.stdout),{
                "time":15,"grips":1,"controls":"advantaged_takedown_top","posture":"lying"})

    def test_object_strike_has_shipped_selector_and_native_http_choice(self):
        status,page=self.request("/")
        self.assertEqual(status,200)
        self.assertIn("function submitObjectStrike(handle,motion,weaponHandle=null)",page)
        self.assertIn("/api/generated/object-strike",page)
        self.assertIn("function submitCoupDeGrace(handle,motion)",page)
        self.assertIn("/api/generated/coup-de-grace",page)
        self.assertIn("function submitBreakWeapon(handle)",page)
        self.assertIn("/api/generated/break-weapon",page)
        profile=json.loads((ROOT/"tests/fixtures/arena/starter.json").read_text())
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261107,
            ground_loadout_profile=profile)
        status,generated=self.request("/api/generated/generate",{
            "starting_experience":"10000","width_cells":"10","height_cells":"5",
            "equipment_mode":"equipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        break_row=next(item for item in generated['action_catalog']['entries']
                       if item['name'].casefold()=='break weapon (armed)')
        self.assertEqual(break_row['status'],'unavailable')
        self.assertIn('opposing Being',break_row['reason'])
        candidate=self.session.active_candidate
        player=candidate.participants[0].native.being
        encounter=candidate.encounter
        from dataclasses import replace
        ground_id=next(key for key in encounter.non_being_object_list
            if candidate.universe.get_object_by_id(key).parent_container_id is None)
        ground=candidate.universe.get_object_by_id(ground_id)
        origin=player.get_position()
        from spatial.state import CartesianPosition
        ground.set_position(CartesianPosition(origin.x+0.1,origin.y,origin.z))
        ledger=player._arena_perception_ledger
        row=ledger._current[ground_id]
        updated=replace(row,position=ground.get_position())
        ledger._current[ground_id]=updated
        ledger._history=[updated if evidence.entity_id==ground_id else evidence
                         for evidence in ledger._history]
        handle=self.session._view_handles[ground_id]
        self.assertEqual(self.request("/api/generated/run",{})[0],200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        inspected=self.request("/api/generated/inspect",{"handle":handle})
        self.assertEqual(inspected[0],200,inspected[1])
        strike=next(row for row in inspected[1]["action_catalog"]["entries"]
                    if row["name"]=="swing at object")
        self.assertEqual(strike["status"],"available",strike["reason"])
        status,accepted=self.request("/api/generated/object-strike",{
            "handle":handle,"motion":"swing"})
        self.assertEqual(status,200,accepted)
        hp_before = ground.hit_points()
        rng_before = self.session._rng_cursor.state
        from action import Action
        action=next(member.action for choice in candidate.encounter._choice_book._choices.values()
                    for member in choice.members if type(member.action) is Action
                    and member.action.event_type=="strike object")
        self.assertEqual(action.event_type,"strike object")
        self.assertEqual(action.target_id,ground_id)
        # The other generated Being has no modeled physical geometry. The
        # server accepts the native declaration, then conservatively resolves
        # the path as uncertain without consuming combat RNG or damaging the
        # Object. This protects the boundary from a fixture-only success claim.
        while action.resolution is None:
            status, advanced = self.request("/api/generated/advance",{"seconds":1})
            self.assertEqual(status,200,advanced)
        self.assertEqual(action.resolution.outcome,"uncertain_path")
        self.assertEqual(ground.hit_points(),hp_before)
        self.assertEqual(self.session._rng_cursor.state,rng_before)

    def test_coup_de_grace_uses_browser_choice_and_pending_native_save_load(self):
        page=self.request("/")[1]
        self.assertIn("function submitCoupDeGrace(handle,motion)",page)
        profile=json.loads((ROOT/"tests/fixtures/arena/empty.json").read_text())
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261108,
            ground_loadout_profile=profile)
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"10000","width_cells":"10","height_cells":"5",
            "equipment_mode":"equipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate
        target=candidate.participants[1].native.being
        player=candidate.participants[0].native.being
        from dataclasses import replace
        from spatial.state import CartesianPosition
        origin=player.get_position()
        target.set_position(CartesianPosition(origin.x+0.1,origin.y,origin.z))
        player.set_hex_facing(nearest_facing((target.get_position().x-origin.x,
            target.get_position().y-origin.y,target.get_position().z-origin.z)))
        for observer in (player,target):
            ledger=observer._arena_perception_ledger
            if target.id not in ledger._current:continue
            row=ledger._current[target.id]
            updated=replace(row,position=target.get_position())
            ledger._current[target.id]=updated
            ledger._history=[updated if item.entity_id==target.id else item for item in ledger._history]
        from states import StatesList
        states=StatesList();states.load_states(str(ROOT/"src/config/states.tsv"));target.stun(states)
        self.assertEqual(self.request("/api/generated/run",{})[0],200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        handle=self.session._view_handles[target.id]
        inspected=self.request("/api/generated/inspect",{"handle":handle})
        self.assertEqual(inspected[0],200)
        row=next(item for item in inspected[1]["action_catalog"]["entries"]
                 if item["name"]=="coup de grace")
        self.assertEqual(row["status"],"available",row["reason"])
        status,accepted=self.request("/api/generated/coup-de-grace",{
            "handle":handle,"motion":"thrust"})
        self.assertEqual(status,200,accepted)
        self.assertEqual(accepted["coup_de_grace_action"]["status"],"executing")
        save=self.session.save_encounter_bytes()
        restored=GeneratedArenaSession(root_seed_factory=lambda:2)
        view=restored.load_encounter_bytes(save)
        self.assertEqual(view["coup_de_grace_action"]["status"],"executing")
        while view["coup_de_grace_action"]["status"]=="executing":
            view=restored.advance_one_second()
        self.assertEqual(view["coup_de_grace_action"]["status"],"completed")
        self.assertIn(view["coup_de_grace_action"]["outcome"],("critical","fatal"))

    def test_disarm_http_pending_save_load_commits_exact_weapon_to_ground(self):
        page=self.request("/")[1]
        self.assertIn("function submitDisarm(handle,motion,unarmed=false,hand=null)",page)
        self.assertIn("function submitDisarmLanding(handle,column,row)",page)
        profile=json.loads((ROOT/"tests/fixtures/arena/empty.json").read_text())
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261108,
            ground_loadout_profile=profile)
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"10000","width_cells":"10","height_cells":"5",
            "equipment_mode":"equipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate;encounter=candidate.encounter
        player=candidate.participants[0].native.being;defender=candidate.participants[1].native.being
        self.assertTrue(defender.weapons)
        target_weapon=candidate.universe.get_object_by_id(defender.weapons[0])
        self.assertTrue(player.weapons)
        attacking=candidate.universe.get_object_by_id(player.weapons[0])
        player.current.skills.weapon_skills[attacking.original.obj_type]=2
        origin=player.get_position()
        layout=candidate.arena_map.layout
        player_cell=layout.cell_at_position(origin)
        defender_cell=next(cell for cell in layout.neighbors(player_cell) if layout.contains(cell))
        defender_position=layout.center_position(defender_cell,z=origin.z)
        defender.set_position(defender_position)
        player.set_hex_facing(nearest_facing((defender_position.x-origin.x,
                                               defender_position.y-origin.y,0.0)))
        from dataclasses import replace
        for observer in (player,defender):
            ledger=observer._arena_perception_ledger
            row=ledger._current.get(defender.id)
            if row is not None:
                updated=replace(row,position=defender.get_position())
                ledger._current[defender.id]=updated
                ledger._history=[updated if item.entity_id==defender.id else item for item in ledger._history]
        self.assertEqual(self.request("/api/generated/run",{})[0],200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        handle=self.session._view_handles[target_weapon.id]
        accepted_status,accepted=self.request("/api/generated/disarm",{
            "handle":handle,"motion":"thrust"})
        self.assertEqual(accepted_status,200,accepted)
        self.assertEqual(accepted['disarm_action']['status'],'executing')
        wire=self.session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            saved=Path(directory)/'pending-disarm.arena'
            saved.write_bytes(wire)
            continuation=(
                "import json,sys;import tests.test_generated_arena_browser;"
                "from unittest.mock import patch;"
                "from action_evaluation import _ProvisionalRandom,RandomDraw;"
                "from arena_browser_session import GeneratedArenaSession;"
                "s=GeneratedArenaSession(root_seed_factory=lambda:3);"
                "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read());"
                "it=iter((20,1));"
                "defroll=None;"
                "exec('def roll(ctx,dice):\\n value=next(it);ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split(\"+\")[0]),value));return value');"
                "cm=patch.object(_ProvisionalRandom,'roll',roll);cm.start();"
                "exec('while v[\"disarm_action\"][\"status\"]==\"executing\":\\n v=s.advance_one_second()');cm.stop();"
                "w=v['disarm_landing_choice'];c=w['cells'][0];v=s.choose_disarm_landing({'handle':w['handle'],'column':c['column'],'row':c['row']});"
                "o=s.active_candidate.universe.get_object_by_id(sys.argv[2]);"
                "print(json.dumps({'action':v['disarm_action'],'owner':o.parent_container_id,"
                "'position':None if o.get_position() is None else o.get_position().as_tuple(),"
                "'inspection':s.active_candidate.encounter.inspect_committed().target(o.id).position.as_tuple()}))")
            child=subprocess.run([sys.executable,'-c',continuation,str(saved),target_weapon.id],
                cwd=ROOT,check=True,capture_output=True,text=True)
        foreign=json.loads(child.stdout)
        self.assertEqual(foreign['action']['outcome'],'landing_choice_pending')
        self.assertIsNone(foreign['owner'])
        self.assertEqual(foreign['position'],foreign['inspection'])
        restored=GeneratedArenaSession(root_seed_factory=lambda:3)
        view=restored.load_encounter_bytes(wire)
        self.assertEqual(view['disarm_action']['status'],'executing')
        from action_evaluation import _ProvisionalRandom,RandomDraw
        draws=iter((20,1))
        def roll(ctx,dice):
            value=next(draws);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):
            while view['disarm_action']['status']=='executing':
                view=restored.advance_one_second()
        self.assertEqual(view['disarm_action']['status'],'completed')
        self.assertEqual(view['disarm_action']['outcome'],'landing_choice_pending')
        self.assertGreaterEqual(view['disarm_action']['maximum_landing_hexes'],0)
        self.assertTrue(view['disarm_landing_choice']['cells'])
        cell=view['disarm_landing_choice']['cells'][0]
        weapon_handle=view['disarm_landing_choice']['handle']
        self.session=restored
        status,view=self.request("/api/generated/disarm-landing",{
            'handle':weapon_handle,
            'column':cell['column'],'row':cell['row']})
        self.assertEqual(status,200,view)
        observed=next(row for row in view['entities']
                      if row['handle']==weapon_handle)
        self.assertEqual(observed['present_state'],'ground')
        self.assertEqual(observed['cell'],cell)
        weapon=restored.active_candidate.universe.get_object_by_id(target_weapon.id)
        self.assertIsNone(weapon.parent_container_id)
        self.assertEqual(weapon.get_position(),restored.active_candidate.encounter.inspect_committed().target(weapon.id).position)
        resolved_wire=restored.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            saved=Path(directory)/'resolved-disarm.arena';saved.write_bytes(resolved_wire)
            code=("import json,sys;import tests.test_generated_arena_browser;"
                "from arena_browser_session import GeneratedArenaSession;"
                "s=GeneratedArenaSession(root_seed_factory=lambda:4);s.load_encounter_bytes(open(sys.argv[1],'rb').read());"
                "o=s.active_candidate.universe.get_object_by_id(sys.argv[2]);"
                "print(json.dumps({'position':o.get_position().as_tuple(),'inspection':"
                "s.active_candidate.encounter.inspect_committed().target(o.id).position.as_tuple()}))")
            child=subprocess.run([sys.executable,'-c',code,str(saved),target_weapon.id],
                cwd=ROOT,check=True,capture_output=True,text=True)
        resolved=json.loads(child.stdout)
        self.assertEqual(resolved['position'],resolved['inspection'])

    def test_generated_zero_range_disarm_lands_in_defender_hex_and_restores(self):
        profile=json.loads((ROOT/"tests/fixtures/arena/empty.json").read_text())
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261108,
            ground_loadout_profile=profile)
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"10000","width_cells":"10","height_cells":"5",
            "equipment_mode":"equipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate;encounter=candidate.encounter
        player=candidate.participants[0].native.being;defender=candidate.participants[1].native.being
        weapon=candidate.universe.get_object_by_id(defender.weapons[0])
        attacking=candidate.universe.get_object_by_id(player.weapons[0])
        player.current.skills.weapon_skills[attacking.original.obj_type]=2
        origin=player.get_position()
        layout=candidate.arena_map.layout
        player_cell=layout.cell_at_position(origin)
        defender_cell=next(cell for cell in layout.neighbors(player_cell) if layout.contains(cell))
        defender_position=layout.center_position(defender_cell,z=origin.z)
        defender.set_position(defender_position)
        player.set_hex_facing(nearest_facing((defender_position.x-origin.x,
                                               defender_position.y-origin.y,0.0)))
        from dataclasses import replace
        for observer in (player,defender):
            ledger=observer._arena_perception_ledger
            row=ledger._current.get(defender.id)
            if row is not None:
                updated=replace(row,position=defender.get_position())
                ledger._current[defender.id]=updated
                ledger._history=[updated if item.entity_id==defender.id else item
                                 for item in ledger._history]
        self.assertEqual(self.request("/api/generated/run",{})[0],200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        handle=self.session._view_handles[weapon.id]
        status,view=self.request("/api/generated/disarm",{"handle":handle,"motion":"thrust"})
        self.assertEqual(status,200,view)
        wire=self.session.save_encounter_bytes()
        restored=GeneratedArenaSession(root_seed_factory=lambda:5)
        view=restored.load_encounter_bytes(wire)
        from action_evaluation import _ProvisionalRandom,RandomDraw
        draws=iter((14,10))
        def roll(ctx,dice):
            value=next(draws);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):
            while view['disarm_action']['status']=='executing':
                view=restored.advance_one_second()
        self.assertEqual(view['disarm_landing_choice']['maximum_landing_hexes'],0)
        self.assertEqual(len(view['disarm_landing_choice']['cells']),1)
        cell=view['disarm_landing_choice']['cells'][0]
        defender_cell=restored.active_candidate.arena_map.layout.cell_at_position(
            restored.active_candidate.participants[1].native.being.get_position())
        self.assertEqual((cell['column'],cell['row']),
                         (defender_cell.column,defender_cell.row))
        landing_handle=view['disarm_landing_choice']['handle']
        self.session=restored
        status,view=self.request('/api/generated/disarm-landing',{
            'handle':landing_handle,'column':cell['column'],'row':cell['row']})
        self.assertEqual(status,200,view)
        observed=next(row for row in view['entities'] if row['handle']==landing_handle)
        self.assertEqual(observed['present_state'],'ground')
        self.assertEqual(observed['cell'],cell)
        dropped=restored.active_candidate.universe.get_object_by_id(weapon.id)
        self.assertEqual(dropped.get_position(),
            restored.active_candidate.participants[1].native.being.get_position())
        resolved=restored.save_encounter_bytes()
        code=("import json,sys;import tests.test_generated_arena_browser;"
            "from arena_browser_session import GeneratedArenaSession;"
            "s=GeneratedArenaSession(root_seed_factory=lambda:6);"
            "s.load_encounter_bytes(open(sys.argv[1],'rb').read());"
            "o=s.active_candidate.universe.get_object_by_id(sys.argv[2]);"
            "p=s.active_candidate.participants[0].native.being._arena_perception_ledger.current;"
            "e=next(r for r in p if r.entity_id==sys.argv[2]);"
            "a=s.active_candidate.arena_map.layout.cell_at_position(e.position);"
            "print(json.dumps({'cell':{'column':a.column,'row':a.row},"
            "'position':o.get_position().as_tuple(),'owner':o.parent_container_id}))")
        with tempfile.TemporaryDirectory() as directory:
            saved=Path(directory)/'zero-range-disarm.arena';saved.write_bytes(resolved)
            child=subprocess.run([sys.executable,'-c',code,str(saved),weapon.id],
                cwd=ROOT,check=True,capture_output=True,text=True)
        final=json.loads(child.stdout)
        self.assertEqual(final['cell'],cell)
        self.assertIsNone(final['owner'])

    def test_generated_arena_exposes_and_accepts_unarmed_disarm(self):
        status,page=self.request("/")
        self.assertEqual(status,200)
        self.assertIn("Disarm custody result",page)
        self.assertIn("Take in ${value}",page)
        profile=json.loads((ROOT/"tests/fixtures/arena/empty.json").read_text())
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261108,
            ground_loadout_profile=profile)
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"10000","width_cells":"10","height_cells":"5",
            "equipment_mode":"equipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate
        player=candidate.participants[0].native.being;defender=candidate.participants[1].native.being
        player.current.skills.skills['unarmed combat']=1
        player.strategy.attack=100
        defender.strategy.defense=0
        free_hand=next((hand for hand in ('left hand','right hand')
                        if player.current.body_parts.get(hand) is None),None)
        if free_hand is None:
            free_hand='left hand';player.current.body_parts[free_hand]=None
        target_weapon=candidate.universe.get_object_by_id(defender.weapons[0])
        origin=player.get_position()
        defender.set_position(CartesianPosition(origin.x+.1,origin.y,origin.z))
        player.set_hex_facing(nearest_facing((.1,0,0)))
        self.assertEqual(self.request("/api/generated/run",{})[0],200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        handle=self.session._view_handles[target_weapon.id]
        inspected=self.request("/api/generated/inspect",{"handle":handle})[1]
        row=next(item for item in inspected["action_catalog"]["entries"]
                 if item["name"]=="disarm (unarmed)")
        self.assertEqual(row["status"],"available",row["reason"])
        self.assertEqual({item["motion"] for item in row["motions"]},{"swing","thrust"})
        self.assertIn(free_hand,row["take_hands"])
        status,accepted=self.request("/api/generated/disarm",{
            "handle":handle,"motion":"thrust","unarmed":True,"hand":free_hand})
        self.assertEqual(status,200,accepted)
        self.assertEqual(accepted["disarm_action"]["status"],"executing")
        wire=self.session.save_encounter_bytes()
        restored=GeneratedArenaSession(root_seed_factory=lambda:3)
        view=restored.load_encounter_bytes(wire)
        from action_evaluation import _ProvisionalRandom,RandomDraw
        rolls=iter((20,1))
        def roll(ctx,dice):
            value=next(rolls)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll):
            while view['disarm_action']['status']=='executing':
                view=restored.advance_one_second()
        self.assertEqual(view['disarm_action']['outcome'],'disarmed_taken')
        taken=restored.active_candidate.universe.get_object_by_id(target_weapon.id)
        restored_defender=restored.active_candidate.encounter.get_being(defender.id)
        restored_player=restored.active_candidate.encounter.get_being(player.id)
        self.assertEqual(taken.parent_container_id,restored_player.id)
        self.assertEqual(restored_player.current.body_parts[free_hand],target_weapon.id)
        self.assertIsNone(restored_defender.current.body_parts.get('right hand'))

        with tempfile.TemporaryDirectory() as directory:
            saved=Path(directory)/'pending-unarmed-disarm-take.arena'
            saved.write_bytes(wire)
            child_code=(
                "import json,sys;import tests.test_generated_arena_browser;"
                "from unittest.mock import patch;"
                "from action_evaluation import _ProvisionalRandom,RandomDraw;"
                "from arena_browser_session import GeneratedArenaSession;"
                "s=GeneratedArenaSession(root_seed_factory=lambda:8);"
                "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read());it=iter((20,1));"
                "exec('def roll(ctx,dice):\\n value=next(it);ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split(\"+\")[0]),value));return value');"
                "cm=patch.object(_ProvisionalRandom,'roll',roll);cm.start();"
                "exec('while v[\"disarm_action\"][\"status\"]==\"executing\":\\n v=s.advance_one_second()');cm.stop();"
                "e=s.active_candidate.encounter;w=s.active_candidate.universe.get_object_by_id(sys.argv[2]);"
                "a=e.get_being(sys.argv[3]);d=e.get_being(sys.argv[4]);"
                "print(json.dumps({'outcome':v['disarm_action']['outcome'],'object':w.id,'owner':w.parent_container_id,'hand':a.current.body_parts[sys.argv[5]],'defender_hand':d.current.body_parts.get('right hand')}))")
            child=subprocess.run([sys.executable,'-c',child_code,str(saved),target_weapon.id,
                player.id,defender.id,free_hand],cwd=ROOT,check=True,capture_output=True,text=True)
        self.assertEqual(json.loads(child.stdout),{
            'outcome':'disarmed_taken','object':target_weapon.id,'owner':player.id,
            'hand':target_weapon.id,'defender_hand':None})

    def test_break_weapon_http_choice_restores_pending_actual_weapon_action(self):
        status,page=self.request("/")
        self.assertEqual(status,200)
        self.assertIn("function submitBreakWeapon(handle)",page)
        self.assertIn("/api/generated/break-weapon",page)
        self.session=GeneratedArenaSession(root_seed_factory=lambda:20261109,
            ground_loadout_profile=json.loads((ROOT/"tests/fixtures/arena/empty.json").read_text()))
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"5000000","width_cells":"10","height_cells":"5",
            "equipment_mode":"equipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        candidate=self.session.active_candidate
        encounter=candidate.encounter
        player=candidate.participants[0].native.being
        opponent=candidate.participants[1].native.being
        # This test-authored native Arena starts with represented close positions
        # and an actual opposing weapon; the browser receives only its opaque
        # perceived Being handle.
        from spatial.state import CartesianPosition
        origin=player.get_position()
        opponent.set_position(CartesianPosition(origin.x+.1,origin.y,origin.z))
        player.set_hex_facing(nearest_facing((.1,0,0)))
        from melee_combat import MeleeStrike
        opponent_weapon=next(iter(opponent.armed_with(candidate.universe).values()))
        opponent_weapon_obj=candidate.universe.get_object_by_id(opponent_weapon)
        opponent_weapon_obj.current.hit_points=1
        opponent_weapon_obj.current.hardness=0
        from action import Action
        attack=MeleeStrike(encounter,opponent.id,player.id,opponent_weapon,
            motion='thrust',reach=2)
        attack.end_time=7
        self.assertEqual(self.request("/api/generated/run",{})[0],200)
        self.assertEqual(self.request("/api/generated/advance",{"seconds":1})[0],200)
        attack.start_time=encounter.time
        attack.end_time=encounter.time+6
        encounter.schedule_action(attack)
        status,view=self.request("/api/generated/advance",{"seconds":1})
        self.assertEqual(status,200,view)
        handle=self.session._view_handles[opponent.id]
        inspected=self.request("/api/generated/inspect",{"handle":handle})
        self.assertEqual(inspected[0],200,inspected[1])
        row=next(item for item in inspected[1]["action_catalog"]["entries"]
                 if item["name"].casefold()=="break weapon (armed)")
        self.assertEqual(row["status"],"available",row["reason"])
        status,accepted=self.request("/api/generated/break-weapon",{"handle":handle})
        self.assertEqual(status,200,accepted)
        action=next(member.action for choice in encounter._choice_book._choices.values()
            for member in choice.members if type(member.action) is Action
            and member.action.event_type=="break weapon")
        self.assertEqual(action.break_weapon_id,opponent_weapon)
        saved=self.session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"pending-break.json";path.write_bytes(saved)
            script="\n".join((
                "import json,sys",
                "from unittest.mock import patch",
                "from action_evaluation import _ProvisionalRandom,RandomDraw",
                "from arena_browser_session import GeneratedArenaSession",
                "s=GeneratedArenaSession(root_seed_factory=lambda:1)",
                "v=s.load_encounter_bytes(open(sys.argv[1],'rb').read())",
                "c=s.active_candidate",
                "pair=next((r,m) for r in c.encounter._choice_book._choices.values() for m in r.members if getattr(m.action,'event_type',None)=='break weapon')",
                "r,m=pair; a=m.action",
                "target=next(m.action for r in c.encounter._choice_book._choices.values() for m in r.members if getattr(m.action,'id',None)==sys.argv[2])",
                "assert a.break_weapon_id==sys.argv[3] and c.encounter.time==2 and r.view.state=='accepted'",
                "values=iter((20,20,4,4,4)); original=_ProvisionalRandom.roll",
                "def roll(ctx,dice):",
                "    if ctx.action_id==a.id:",
                "        value=next(values); ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value)); return value",
                "    return original(ctx,dice)",
                "patcher=patch.object(_ProvisionalRandom,'roll',roll); patcher.start()",
                "while a.id not in c.encounter.finished_action_list and c.encounter.time<7: v=s.advance_one_second()",
                "break_outcome=c.encounter.inspect_committed(6).action(a.id).facts.outcome; hp=c.universe.get_object_by_id(a.break_weapon_id).hit_points()",
                "while target.id not in c.encounter.finished_action_list and c.encounter.time<7: v=s.advance_one_second()",
                "patcher.stop(); attack_outcome=c.encounter.inspect_committed(7).action(target.id).facts.outcome",
                "print(json.dumps({'time':c.encounter.time,'weapon':a.break_weapon_id,'action':a.id,'finished':a.id in c.encounter.finished_action_list,'break':break_outcome,'hp':hp,'attack':attack_outcome}))"))
            env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join((str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'examples')))
            restored=subprocess.run([sys.executable,"-B","-c",script,str(path),attack.id,opponent_weapon],cwd=ROOT,env=env,
                check=False,capture_output=True,text=True,timeout=90)
            self.assertEqual(restored.returncode,0,restored.stderr)
            evidence=json.loads(restored.stdout)
            self.assertEqual({key:evidence[key] for key in ('time','weapon','action','finished')},
                {"time":7,"weapon":opponent_weapon,"action":action.id,"finished":True})
            self.assertEqual(evidence['break'],'broken')
            self.assertEqual(evidence['hp'],0)
            self.assertEqual(evidence['attack'],'weapon_unavailable')

    def test_armed_feint_uses_browser_route_and_pending_save_load(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("function submitFeint(handle,motion,unarmed=false", page)
        self.assertIn("/api/generated/feint", page)
        self.assertIn("actionFeint", page)
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261107,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "5000000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        status, activated = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        player = self.session.active_candidate.participants[0].native.being
        self.assertGreater(player.current.skills.weapon_skills.get("Dagger", 0), 1)
        target_id = self.session.active_candidate.participants[1].native.being.id
        target = next(row for row in activated["entities"]
                      if row["category"] == "being"
                      and self.session._view_handles[target_id] == row["handle"])
        status, selected = self.request("/api/generated/inspect", {"handle": target["handle"]})
        self.assertEqual(status, 200)
        feint = next(row for row in selected["action_catalog"]["entries"]
                     if row["name"] == "feint (armed)")
        self.assertEqual(feint["status"], "available", feint["reason"])
        status, accepted = self.request("/api/generated/feint", {
            "handle": target["handle"], "motion": "thrust"})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["feint_action"]["status"], "executing")
        pending = self.session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "pending-feint.json"
            save_path.write_bytes(pending)
            script = (
                "import json,sys; import tests.test_generated_arena_browser; "
                "from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:8); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "v=s._view_unlocked();\n"
                "while v['feint_action']['status']=='executing':\n v=s.advance_one_second()\n"
                "print(json.dumps({'view':v,'save':s.save_encounter_bytes().decode('utf8')}))")
            process = subprocess.run([sys.executable, "-c", script, str(save_path)],
                cwd=ROOT, check=True, capture_output=True, text=True)
            restored = json.loads(process.stdout)
        completed = self.session._view_unlocked()
        while completed["feint_action"]["status"] == "executing":
            completed = self.session.advance_one_second()
        self.assertEqual(restored["view"]["time_seconds"], completed["time_seconds"])
        self.assertEqual(restored["view"]["feint_action"], completed["feint_action"])
        self.assertEqual(completed["feint_action"]["status"], "completed")
        native = self.session.active_candidate.encounter.inspect_committed(
            int(completed["time_seconds"]))
        receipt = native.action(self.session._player_feint_action(
            self.session.active_candidate, player).id)
        self.assertIn(receipt.facts.outcome, ("success", "failure", "out_of_reach"))
        self.assertFalse(receipt.facts.effects)
        for key in ("name", "hex_facing", "posture", "cell", "position_meters"):
            self.assertEqual(restored["view"]["player"][key], completed["player"][key])
        completed_restore = GeneratedArenaSession(root_seed_factory=lambda: 9)
        restored_completed = completed_restore.load_encounter_bytes(
            restored["save"].encode("utf-8"))
        self.assertEqual(restored_completed["time_seconds"], completed["time_seconds"])
        self.assertEqual(restored_completed["feint_action"], completed["feint_action"])

    def test_unarmed_feint_is_composed_by_shipped_ui_and_survives_fresh_load(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("Unarmed Feint body profile and motion", page)
        self.assertIn("body_region:item.body_region", page)
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261108,
            ground_loadout_profile=json.loads(
                (ROOT / "tests/fixtures/arena/empty.json").read_text()))
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "5000000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        player.current.skills.skills['unarmed combat'] = 2
        player.current.skills.weapon_skills['Dagger'] = 2
        initial_position = player.get_position()
        target.set_position(CartesianPosition(initial_position.x + 0.2,
            initial_position.y, initial_position.z))
        player.set_hex_facing(nearest_facing((1.0, 0.0, 0.0)))
        candidate.encounter.difficulty_class = 1
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        status, activated = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        target_handle = self.session._view_handles[target.id]
        target_row = next(row for row in activated["entities"]
            if row["category"] == "being" and row["handle"] == target_handle)
        status, selected = self.request("/api/generated/inspect", {"handle": target_row["handle"]})
        self.assertEqual(status, 200)
        feint = next(row for row in selected["action_catalog"]["entries"]
                     if row["name"] == "feint (unarmed)")
        self.assertEqual(feint["status"], "available", feint["reason"])
        self.assertIn({"motion": "thrust", "body_region": "Arm",
                      "duration_seconds": 2}, feint["motions"])
        status, accepted = self.request("/api/generated/feint", {
            "handle": target_row["handle"], "motion": "thrust",
            "unarmed": True, "body_region": "Arm"})
        self.assertEqual(status, 200, accepted)
        self.assertEqual(accepted["feint_action"]["status"], "executing")
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "pending-unarmed-feint.arena"
            save_path.write_bytes(self.session.save_encounter_bytes())
            script = (
                "import json,sys; import tests.test_generated_arena_browser; "
                "from arena_browser_session import GeneratedArenaSession; "
                "s=GeneratedArenaSession(root_seed_factory=lambda:91); "
                "s.load_encounter_bytes(open(sys.argv[1],'rb').read()); "
                "v=s._view_unlocked();\n"
                "while v['feint_action']['status']=='executing':\n v=s.advance_one_second()\n"
                "c=s.active_candidate; a=c.participants[0].native.being; "
                "f=s._player_feint_action(c,a); "
                "r=c.encounter.inspect_committed(int(v['time_seconds'])).action(f.id); "
                "handle=s._view_handles[f.target_id]; s.choose_melee_strike({'handle':handle,'motion':'thrust'}); "
                "strike=next(m.action for rec in c.encounter._choice_book._choices.values() for m in rec.members "
                "if type(m.action).__name__=='MeleeStrike' and m.action.actor_id==a.id); "
                "print(json.dumps({'view':v,'outcome':r.facts.outcome,'effects':list(r.facts.effects),"
                "'region':f.body_region,'instrument':f.instrument_id,'action_id':f.id,"
                "'followup_feint_source':strike.feint_source_action_id}))")
            child_env = dict(os.environ)
            child_env['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'tests'),
                str(ROOT / 'src'), str(ROOT / 'examples')))
            process = subprocess.run([sys.executable, "-c", script, str(save_path)],
                cwd=ROOT, env=child_env, check=False, capture_output=True,
                text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stderr)
            restored = json.loads(process.stdout)
        self.assertEqual(restored['outcome'], 'success')
        self.assertEqual(restored['effects'], [])
        self.assertEqual(restored['region'], 'Arm')
        self.assertIsNone(restored['instrument'])
        self.assertEqual(restored['view']['feint_action']['status'], 'completed')
        self.assertEqual(restored['followup_feint_source'], restored['action_id'])

    def test_attack_only_browser_requests_drive_native_approach_and_thrust(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text())
        self.session = GeneratedArenaSession(
            root_seed_factory=lambda: 20261123, ground_loadout_profile=profile)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "attack_only"})
        self.assertEqual(status, 200)
        self.assertEqual(generated["opponent_activity"], "waiting")
        candidate = self.session.active_candidate
        opponent = candidate.participants[1].native.being
        initial_opponent_position = opponent.get_position()
        status, accepted = self.request("/api/generated/run", {})
        self.assertEqual(status, 200)
        self.assertTrue(accepted["advance_available"])
        status, approached = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(approached["time_seconds"], 1)
        self.assertEqual(approached["opponent_activity"], "approaching")
        first_position = opponent.get_position()
        self.assertNotEqual(first_position, initial_opponent_position)
        self.assertEqual(self.session._opponent_decision(candidate)["kind"], "move")
        status, attack_ready = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        attack_position = opponent.get_position()
        self.assertNotEqual(attack_position, first_position)
        self.assertEqual(attack_ready["opponent_activity"], "attack opportunity")
        status, pending = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(opponent.get_position(), attack_position)
        self.assertEqual(pending["opponent_melee_action"]["status"], "executing")
        self.assertEqual(pending["opponent_melee_action"]["seconds_remaining"], 3)
        self.assertNotIn(opponent.id, json.dumps(pending))
        encoded_pending = json.dumps(pending).lower()
        self.assertNotIn('"destination_cell"', encoded_pending)
        self.assertNotIn('"destination_position_meters"', encoded_pending)
        page_status, page = self.request("/")
        self.assertEqual(page_status, 200)
        self.assertIn("Opponent is approaching.", page)
        self.assertIn("s.opponent_activity==='attack opportunity'", page)

    def test_seeded_two_sided_browser_combat_hit_and_fresh_process_continuation(self):
        from action_evaluation import DamageEffect
        from melee_combat import MeleeStrike

        self.session = GeneratedArenaSession(root_seed_factory=lambda: 14)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "attack_only",
            "root_seed": "14"})
        self.assertEqual(status, 200, generated)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, opponent = (row.native.being for row in candidate.participants)
        player_hp_before, opponent_hp_before = player.get_hit_points(), opponent.get_hit_points()
        self.assertEqual([candidate.universe.get_object_by_id(value).current.obj_type
                          for value in player.weapons], ["Dagger"])
        self.assertEqual([candidate.universe.get_object_by_id(value).current.obj_type
                          for value in opponent.weapons], ["Dagger"])

        status, moved = self.request("/api/generated/destination", {
            "column": 8, "row": 1, "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200, moved)
        status, moved = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual((status, moved["time_seconds"], moved["player"]["cell"]),
                         (200, 1, {"column": 8, "row": 1}))
        self.assertEqual(moved["player"]["hex_facing"], 5)
        target_handle = self.session._view_handles[opponent.id]
        target_view = self.session.inspect_entity({"handle": target_handle})
        self.assertIsNone(target_view["selected_being"]["condition"]["hit_points_current"])
        self.assertIn("Unknown", target_view["selected_being"]["condition"]["status"])
        status, accepted = self.request("/api/generated/action-program", {"components": [{
            "kind": "melee", "handle": target_handle, "motion": "thrust"}]})
        self.assertEqual(status, 200, accepted)
        strike = next(member.action for record in encounter._choice_book._choices.values()
                      for member in record.members
                      if type(member.action) is MeleeStrike and member.action.actor_id == player.id)
        self.assertEqual(strike.instrument_id, next(iter(player.weapons)))
        for _ in range(4):
            status, state = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200, state)
        self.assertEqual(state["time_seconds"], 5)
        player_record = encounter.inspect_committed(5).action(strike.id)
        self.assertEqual(player_record.facts.outcome, "normal")
        self.assertTrue(any(type(effect) is DamageEffect and effect.amount > 0
                            for effect in player_record.facts.effects))
        self.assertLess(opponent.get_hit_points(), opponent_hp_before)
        player_melee_view = state["melee_action"]
        self.assertEqual(player_melee_view["result_label"], "hit")
        self.assertTrue(player_melee_view["damage_committed"])
        self.assertEqual(player_melee_view["weapon_name"], "Dagger")
        self.assertEqual(player_melee_view["impact_distance_meters"],
                         dict(player_record.facts.metadata)["distance"])
        status, state = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual((status, state["time_seconds"]), (200, 6))
        opponent_strikes = [action for action in self.session._all_melee_actions(candidate)
                            if action.actor_id == opponent.id]
        self.assertTrue(opponent_strikes)
        self.assertTrue(any(action.id in encounter.finished_action_list
                            and encounter.inspect_committed(5).action(action.id).facts.outcome
                            == "normal" for action in opponent_strikes))
        self.assertLess(player.get_hit_points(), player_hp_before)
        observer = json.dumps(state)
        self.assertNotIn(opponent.id, observer)

        with tempfile.TemporaryDirectory(prefix="arena-two-sided-fresh-process-") as temp:
            save_path = Path(temp) / "chrome-equivalent-save.json"
            save_path.write_bytes(self.session.save_encounter_bytes())
            child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                             PYTHONPATH=os.pathsep.join((str(ROOT / "tests"),
                                 str(ROOT / "src"), str(ROOT / "examples"))))
            child_code = """import json,sys; from pathlib import Path; from arena_browser_session import GeneratedArenaSession; from melee_combat import MeleeStrike; from action_evaluation import DamageEffect; s=GeneratedArenaSession(); v=s.load_encounter_bytes(Path(sys.argv[1]).read_bytes()); c=s.active_candidate; p,o=(r.native.being for r in c.participants); assert c.encounter.time==6 and c.root_seed==14 and v['opponent_strategy']=='attack_only'; actions=s._all_melee_actions(c); ps=next(a for a in actions if a.actor_id==p.id); pf=c.encounter.inspect_committed(5).action(ps.id).facts; assert pf.outcome=='normal' and any(type(e) is DamageEffect and e.amount>0 for e in pf.effects); os=[a for a in actions if a.actor_id==o.id]; assert any(a.id in c.encounter.finished_action_list and c.encounter.inspect_committed(5).action(a.id).facts.outcome=='normal' for a in os); assert (p.get_hit_points(),o.get_hit_points())==(23,16); [s.advance_one_second() for _ in range(3)]; assert c.encounter.time==9; later=next(a for a in s._all_melee_actions(c) if a.actor_id==o.id and a.start_time==5); assert later.id in c.encounter.finished_action_list; print(json.dumps({'restored':6,'continued':9,'player_hp':p.get_hit_points(),'opponent_hp':o.get_hit_points(),'player_hit':'normal','player_damage':sum(e.amount for e in pf.effects if type(e) is DamageEffect and e.amount>0),'opponent_action_count':len(s._all_melee_actions(c))}))"""
            process = subprocess.run([sys.executable, "-B", "-c", child_code, str(save_path)],
                cwd=ROOT, env=child_env, check=False, capture_output=True,
                text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stderr)
            restored = json.loads(process.stdout)
        self.assertEqual((restored["restored"], restored["continued"]), (6, 9))
        self.assertEqual((restored["player_hp"], restored["opponent_hp"]), (23, 16))
        self.assertGreater(restored["player_damage"], 0)
        self.assertGreaterEqual(restored["opponent_action_count"], 2)

    def test_pending_passive_shield_hit_restores_and_commits_in_fresh_process(self):
        """A generated-Arena pending strike keeps shield identity across OS processes."""
        from action_evaluation import DamageEffect, ProtectionEffect
        from melee_combat import MeleeStrike

        self.session = GeneratedArenaSession(root_seed_factory=lambda: 14)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "attack_only", "root_seed": "14"})
        self.assertEqual(status, 200, generated)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, defender = (row.native.being for row in candidate.participants)
        shield_id = candidate.universe.make_weapon_for_being(
            defender.id, "Small shield", "Authored passive shield")
        candidate.universe.arm_being(defender.id, shield_id, "shield hand")

        status, moved = self.request("/api/generated/destination", {
            "column": 8, "row": 1, "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200, moved)
        status, moved = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200, moved)
        handle = self.session._view_handles[defender.id]
        status, accepted = self.request("/api/generated/action-program", {
            "components": [{"kind": "melee", "handle": handle, "motion": "thrust"}]})
        self.assertEqual(status, 200, accepted)
        strike = next(member.action for record in encounter._choice_book._choices.values()
            for member in record.members
            if type(member.action) is MeleeStrike and member.action.actor_id == player.id)
        self.session.advance_one_second()
        encounter.allocate_passive_shield_coverage(defender.id, shield_id, (strike.id,))
        pending = self.session.save_encounter_bytes()
        shield_hp_before = candidate.universe.get_object_by_id(shield_id).hit_points()
        with tempfile.TemporaryDirectory(prefix="arena-passive-shield-fresh-process-") as temp:
            pending_path = Path(temp) / "pending-shield-strike.json"
            pending_path.write_bytes(pending)
            child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                PYTHONPATH=os.pathsep.join((str(ROOT / "tests"), str(ROOT / "src"),
                                            str(ROOT / "examples"))))
            code = """import json,sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
from action_evaluation import DamageEffect,ProtectionEffect
s=GeneratedArenaSession();s.load_encounter_bytes(Path(sys.argv[1]).read_bytes())
c=s.active_candidate; strike_id,shield_id,defender_id=sys.argv[2:5]
assert c.encounter.time==2 and c.universe.get_object_by_id(shield_id).hit_points()>0
assert any(row==(5,defender_id,shield_id,(strike_id,))
           for row in c.encounter._shield_allocation_choices), c.encounter._shield_allocation_choices
assert any(a.id==strike_id and a.end_time==5 for a in s._all_melee_actions(c))
for _ in range(3): s.advance_one_second()
facts=c.encounter.inspect_committed(5).action(strike_id).facts
assert facts.outcome=='normal', (facts.outcome, facts.effects)
protection=next(x for x in facts.effects if type(x) is ProtectionEffect
                and x.layer=='shield' and x.target_id==shield_id)
damage=sum(x.amount for x in facts.effects if type(x) is DamageEffect
           and x.target_id==shield_id and x.component=='shield')
shield=c.universe.get_object_by_id(shield_id)
assert damage==(max(0,protection.incoming-int(shield.get_weapon_size()))
                if protection.intercepted else 0)
assert shield.hit_points()==int(sys.argv[5])-damage
print(json.dumps({'time':c.encounter.time,'outcome':facts.outcome,'shield_id':shield.id,
                  'damage':damage,'shield_hp':shield.hit_points(),'intercepted':protection.intercepted,
                  'incoming':protection.incoming,'passed':protection.passed}))"""
            process = subprocess.run([sys.executable, "-B", "-c", code,
                str(pending_path), strike.id, shield_id, defender.id,
                str(shield_hp_before)], cwd=ROOT,
                env=child_env, capture_output=True, text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stderr)
            restored = json.loads(process.stdout)
        self.assertEqual(restored["time"], 5)
        self.assertEqual(restored["outcome"], "normal")
        self.assertEqual(restored["shield_id"], shield_id)
        self.assertTrue(restored["intercepted"])
        self.assertEqual((restored["incoming"], restored["passed"], restored["damage"]),
                         (2, 0, 0))

    def test_observer_safe_zero_cost_shield_allocation_control(self):
        from melee_combat import MeleeStrike
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 14)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "equipped", "opponent_strategy": "none", "root_seed": "14"})
        self.assertEqual(status, 200, generated)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, opponent = (row.native.being for row in candidate.participants)
        shield_id = candidate.universe.make_weapon_for_being(player.id,
            "Small shield", "Player allocation shield")
        candidate.universe.arm_being(player.id, shield_id, "shield hand")
        status, _ = self.request("/api/generated/destination", {
            "column": 8, "row": 1, "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        status, _ = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        weapon_id = next(iter(opponent.armed_with(candidate.universe).values()))
        strike = MeleeStrike(encounter, opponent.id, player.id, weapon_id,
                             motion="swing", reach=20)
        encounter.schedule_action(strike)
        self.session.advance_one_second()
        state = self.session._view_unlocked()
        entry = next(row for row in state["action_catalog"]["entries"]
                     if row["name"] == "Allocate passive shield coverage")
        self.assertEqual(len(entry["attack_options"]), 1)
        before_time = encounter.time
        before_reservations = encounter.active_reservations
        status, accepted = self.request("/api/generated/shield-allocation", {
            "shield_handle": entry["shield_handle"],
            "attack_handles": [entry["attack_options"][0]["handle"]]})
        self.assertEqual(status, 200, accepted)
        self.assertEqual(encounter.time, before_time)
        self.assertEqual(encounter.active_reservations, before_reservations)
        self.assertEqual(encounter._shield_allocation_choices[-1],
            (strike.end_time, player.id, shield_id, (strike.id,)))

    def enable_trace(self):
        import io
        stream = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                             trace_ui=True, trace_stream=stream)
        return stream

    def test_fixed_generated_candidates_classify_hp_refusal_and_native_race_import(self):
        import copy
        from movement_intent import MovementIntentRefusal
        from arena_browser_session import _safe_movement_refusal

        # This fixed root reproduces the observed cases in installed npcgen:
        # Human/0 XP is born at 0 HP, while Human/10,000 XP is mobile but the
        # checked-in native Human template has an empty race field.
        import io
        trace = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261108,
                                             trace_ui=True, trace_stream=trace)
        zero_status, zero_view = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(zero_status, 200)
        zero_candidate = self.session.active_candidate
        zero_player = zero_candidate.participants[0].native.being
        self.assertEqual((zero_player.current.obj_type, zero_player.current.race,
                          zero_player.get_hit_points(), zero_player.hex_facing),
                         ("Human", "Human", 0, 3))
        zero_start = zero_player.get_position()
        zero_address = max(zero_candidate.arena_map.layout.addresses(), key=lambda cell: math.dist(
            zero_candidate.arena_map.layout.center_position(cell, z=zero_start.z).as_tuple(),
            zero_start.as_tuple()))
        selected = self.request("/api/generated/destination", {
            "column": zero_address.column, "row": zero_address.row,
            "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(selected[0], 200)

        ledger = object.__getattribute__(zero_player, "__dict__")["_arena_perception_ledger"]
        opponent = zero_candidate.participants[1].native.being
        before = {
            "time": zero_candidate.encounter.time,
            "position": zero_player.get_position(),
            "facing": zero_player.hex_facing,
            "plan": self.session._movement_plan,
            "rng": self.session._rng_cursor.state,
            "global_rng": random.getstate(),
            "history": copy.copy(zero_candidate.universe.event_history),
            "pending": list(zero_candidate.encounter.pending_action_list),
            "choices": zero_candidate.encounter.choice_state,
            "awareness": (tuple(zero_candidate.encounter.aware_beings(zero_player.id)),
                          tuple(zero_candidate.encounter.aware_beings(opponent.id))),
            "evidence": tuple(ledger.current),
        }
        status, refusal = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 409)
        self.assertEqual(refusal["movement_refusal"], {
            "category": "actor_unable_to_move",
            "message": ("Your Being is at 0 HP or below and cannot take voluntary movement under "
                        "the adopted rules. No Encounter time or position changed; your destination "
                        "plan remains selected."),
        })
        self.assertEqual(zero_candidate.encounter.time, before["time"])
        self.assertEqual(zero_player.get_position(), before["position"])
        self.assertEqual(zero_player.hex_facing, before["facing"])
        self.assertIs(self.session._movement_plan, before["plan"])
        self.assertEqual(self.session._rng_cursor.state, before["rng"])
        self.assertEqual(random.getstate(), before["global_rng"])
        self.assertEqual(zero_candidate.universe.event_history, before["history"])
        self.assertEqual(list(zero_candidate.encounter.pending_action_list), before["pending"])
        self.assertEqual(zero_candidate.encounter.choice_state, before["choices"])
        self.assertEqual((tuple(zero_candidate.encounter.aware_beings(zero_player.id)),
                          tuple(zero_candidate.encounter.aware_beings(opponent.id))),
                         before["awareness"])
        self.assertEqual(tuple(ledger.current), before["evidence"])
        self.assertEqual(self.session.public_view()["movement_plan"], selected[1]["movement_plan"])
        self.assertNotIn(opponent.id, json.dumps(refusal))
        self.assertNotIn("seed", json.dumps(refusal).lower())
        self.assertNotIn("MovementIntentRefusal", json.dumps(refusal))
        self.assertIn("reason=actor_unable_to_move", trace.getvalue())
        self.assertNotIn("ineligible_actor", trace.getvalue())
        self.assertNotIn(opponent.id, trace.getvalue())
        self.assertTrue(zero_candidate.engine_identity)

        # Privileged integration diagnostics retain the exact native code and
        # message behind the browser-safe refusal category.
        with self.assertRaises(ArenaBrowserRequestError) as native_error:
            self.session.advance_one_second()
        cause = native_error.exception.__cause__
        while cause is not None and not hasattr(cause, "code"):
            cause = cause.__cause__
        self.assertEqual((cause.code, str(cause)),
                         ("ineligible_actor", "a Being at 0 HP or below cannot choose voluntary movement"))
        self.assertEqual(_safe_movement_refusal(MovementIntentRefusal(
            "no_movement_rate", "privileged detail"))["category"], "rate_unavailable")
        self.assertEqual(_safe_movement_refusal(MovementIntentRefusal(
            "unknown_movement_limit", "privileged detail"))["category"],
            "native_prerequisite_unavailable")
        self.assertEqual(_safe_movement_refusal(MovementIntentRefusal(
            "unsupported_race", "private race value"))["category"],
            "unsupported_movement_profile")

        # The same documented root seed at positive XP proves the template
        # race omission was a data-import defect, not a valid race refusal.
        for rate in ("walk", "sprint"):
            self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261108)
            status, generated = self.request("/api/generated/generate", {
                "starting_experience": "10000", "width_cells": "5", "height_cells": "5"})
            self.assertEqual(status, 200)
            candidate = self.session.active_candidate
            player = candidate.participants[0].native.being
            self.assertEqual(player.current.race, "Human")
            self.assertGreater(player.get_hit_points(), 0)
            self.assertEqual(player.hex_facing, 3)
            start = player.get_position()
            target = max(candidate.arena_map.layout.addresses(), key=lambda cell: math.dist(
                candidate.arena_map.layout.center_position(cell, z=start.z).as_tuple(),
                start.as_tuple()))
            status, plan = self.request("/api/generated/destination", {
                "column": target.column, "row": target.row,
                "rate": rate, "facing_policy": "turn"})
            self.assertEqual(status, 200)
            self.assertEqual(plan["movement_plan"]["rate"], rate)
            status, advanced = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            self.assertEqual(advanced["time_seconds"], 1)
            self.assertNotEqual(player.get_position(), start)

        # A distinct generated race/template alias and initial heading remain
        # mobile at zero XP when HP is positive.
        for rate in ("walk", "sprint"):
            self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
            status, _ = self.request("/api/generated/generate", {
                "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
            self.assertEqual(status, 200)
            candidate = self.session.active_candidate
            player = candidate.participants[0].native.being
            self.assertEqual((player.current.obj_type, player.current.race,
                              player.get_hit_points(), player.hex_facing),
                             ("High elf", "Elf", 7, 4))
            start = player.get_position()
            target = max(candidate.arena_map.layout.addresses(), key=lambda cell: math.dist(
                candidate.arena_map.layout.center_position(cell, z=start.z).as_tuple(),
                start.as_tuple()))
            self.assertEqual(self.request("/api/generated/destination", {
                "column": target.column, "row": target.row,
                "rate": rate, "facing_policy": "turn"})[0], 200)
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
            self.assertNotEqual(player.get_position(), start)

    def test_legacy_handler_still_selects_its_original_fixed_scenario_page(self):
        legacy_handler = object.__new__(make_handler(ArenaSession(die_roll=20)))
        legacy_handler.path = "/"
        legacy_handler.wfile = io.BytesIO()
        result = {}
        legacy_handler._send = lambda status, body, content_type="application/json; charset=utf-8": result.update(
            status=status, body=body, content_type=content_type)
        legacy_handler.do_GET()
        self.assertEqual(result["status"], 200)
        self.assertIn("GM / developer Reality view", result["body"])

    def test_empty_page_and_state_offer_native_load_without_an_active_encounter(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('id="saveFile" disabled', page)
        self.assertIn('id="loadFile"', page)
        self.assertIn('id="saveFileInput"', page)
        self.assertIn('/api/generated/save', page)
        self.assertIn('/api/generated/load', page)
        self.assertIn('id="generate" disabled', page)
        self.assertIn('id="spot" disabled', page)
        self.assertIn('id="rate"', page)
        self.assertIn('id="facingPolicy"', page)
        self.assertIn('id="stop"', page)
        self.assertIn("/api/generated/destination", page)
        self.assertIn("/api/generated/stop", page)
        self.assertIn('hex_vertex_offsets_meters', page)
        self.assertIn('ctx.closePath()', page)
        self.assertNotIn("p.column+.5", page)
        status, state = self.request("/api/generated/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["state"], "empty")
        self.assertFalse(state["save_available"])
        self.assertTrue(state["load_available"])
        self.assertFalse(state["spot_available"])
        self.assertIsNone(self.session.active_candidate)
        self.assertEqual(self.request("/api/gm")[0], 404)

    def test_pristine_arena_portable_save_load_and_native_activation(self):
        generated = self.session.generate({"starting_experience": "10000",
            "width_cells": "5", "height_cells": "5"})
        source = self.session.active_candidate
        source_player = source.participants[0].native.being
        source_opponent = source.participants[1].native.being
        wire = self.session.save_encounter_bytes()
        from arena_browser_session import GeneratedArenaSession
        restored = GeneratedArenaSession(root_seed_factory=lambda: 1)
        restored_view = restored.load_encounter_bytes(wire)
        target = restored.active_candidate
        target_player = target.participants[0].native.being
        target_opponent = target.participants[1].native.being
        self.assertEqual(restored_view["time_seconds"], 0)
        self.assertEqual((target_player.id, target_opponent.id),
                         (source_player.id, source_opponent.id))
        from checkpoint_reconstruction import _projection
        self.assertEqual(_projection(target_player.current), _projection(source_player.current))
        self.assertEqual(_projection(target_player.original), _projection(source_player.original))
        self.assertEqual(target_player.get_position(), source_player.get_position())
        self.assertEqual(target.encounter.awareness, source.encounter.awareness)
        self.assertEqual(target_player._arena_perception_ledger.history,
                         source_player._arena_perception_ledger.history)
        self.assertEqual(restored._rng_cursor.state, self.session._rng_cursor.state)
        self.assertEqual(restored_view["entities"][0]["name"], generated["entities"][0]["name"])

        start = target_player.get_position()
        destination = max(target.arena_map.layout.addresses(), key=lambda cell:
            math.dist(target.arena_map.layout.center_position(cell, z=start.z).as_tuple(),
                      start.as_tuple()))
        restored.choose_destination({"column": destination.column, "row": destination.row,
                                     "rate": "walk", "facing_policy": "turn"})
        self.assertTrue(target.encounter.initiated)
        self.assertEqual(target.encounter.progression_mode, "transactional")
        activation_wire = restored.save_encounter_bytes()
        resumed = GeneratedArenaSession(root_seed_factory=lambda: 2)
        resumed.load_encounter_bytes(activation_wire)
        resumed_view = resumed.advance_one_second()
        self.session.choose_destination({"column": destination.column, "row": destination.row,
                                         "rate": "walk", "facing_policy": "turn"})
        uninterrupted_view = self.session.advance_one_second()
        resumed_player = resumed.active_candidate.participants[0].native.being
        uninterrupted_player = self.session.active_candidate.participants[0].native.being
        self.assertEqual(resumed_view["time_seconds"], uninterrupted_view["time_seconds"])
        self.assertEqual(resumed_player.get_position(), uninterrupted_player.get_position())
        self.assertEqual(resumed_player.hex_facing, uninterrupted_player.hex_facing)
        self.assertEqual(resumed._rng_cursor.state, self.session._rng_cursor.state)
        self.assertGreater(len(resumed.save_encounter_bytes()), 0)

    def test_http_save_and_load_use_binary_portable_file_and_atomic_replacement(self):
        self.session.generate({"starting_experience": "10000",
            "width_cells": "5", "height_cells": "5"})
        handler_type = make_handler(self.session)
        save_handler = object.__new__(handler_type)
        save_handler.path = "/api/generated/save"
        save_handler.server = type("FakeServer", (), {"server_port": 8000})()
        save_handler.wfile = io.BytesIO()
        saved = {}
        save_handler._send = lambda status, body, content_type="application/json; charset=utf-8", extra_headers=None: saved.update(
            status=status, body=body, content_type=content_type, headers=extra_headers)
        save_handler.do_GET()
        self.assertEqual(saved["status"], 200)
        self.assertEqual(saved["content_type"], "application/octet-stream")
        wire = saved["body"]
        self.assertTrue(wire.startswith(b'{'))

        replacement = GeneratedArenaSession(root_seed_factory=lambda: 1)
        replacement.generate({"starting_experience": "10000",
            "width_cells": "5", "height_cells": "5"})
        original_candidate = replacement.active_candidate
        load_handler = object.__new__(make_handler(replacement))
        load_handler.path = "/api/generated/load"
        load_handler.server = type("FakeServer", (), {"server_port": 8000})()
        load_handler.wfile = io.BytesIO()
        load_handler.rfile = io.BytesIO(wire)
        load_handler.headers = {"Content-Length": str(len(wire)),
                                "Content-Type": "application/octet-stream"}
        result = {}
        load_handler._send = lambda status, body, content_type="application/json; charset=utf-8", extra_headers=None: result.update(
            status=status, body=body, content_type=content_type)
        load_handler.do_POST()
        self.assertEqual(result["status"], 200)
        self.assertIsNot(replacement.active_candidate, original_candidate)
        self.assertEqual(result["body"]["time_seconds"], 0)

        bad_handler = object.__new__(make_handler(replacement))
        bad_handler.path = "/api/generated/load"
        bad_handler.server = type("FakeServer", (), {"server_port": 8000})()
        bad_handler.wfile = io.BytesIO()
        bad_handler.rfile = io.BytesIO(b"not a save")
        bad_handler.headers = {"Content-Length": "10",
                               "Content-Type": "application/octet-stream"}
        rejected = {}
        bad_handler._send = lambda status, body, content_type="application/json; charset=utf-8", extra_headers=None: rejected.update(
            status=status, body=body)
        candidate_before_bad_load = replacement.active_candidate
        bad_handler.do_POST()
        self.assertEqual(rejected["status"], 409)
        self.assertIs(replacement.active_candidate, candidate_before_bad_load)

    def test_generated_page_is_marked_and_not_reused_from_browser_cache(self):
        handler_type = make_handler(self.session)
        handler = object.__new__(handler_type)
        handler.path = "/"
        handler.server = type("FakeServer", (), {"server_port": 8000})()
        handler.wfile = io.BytesIO()
        response_headers = {}
        handler.send_response = lambda status: response_headers.update(status=status)
        handler.send_header = lambda name, value: response_headers.update({name.lower(): value})
        handler.end_headers = lambda: None
        handler.do_GET()
        self.assertEqual(response_headers["cache-control"], "no-store")
        self.assertEqual(response_headers["x-arena-ui-generation"], "008")
        page = handler.wfile.getvalue().decode("utf-8")
        self.assertIn('<meta name="arena-ui-generation" content="008">', page)

    def test_trace_off_is_quiet_and_diagnostic_route_is_unavailable(self):
        import io
        stream = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                             trace_stream=stream)
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("const traceEnabled=false", page)
        self.assertEqual(self.request("/api/generated/trace", {
            "seq": 1, "event": "advance_clicked"})[0], 404)
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(stream.getvalue(), "")

    def test_trace_events_and_native_advance_report_authoritative_transitions(self):
        from concurrent.futures import ThreadPoolExecutor

        stream = self.enable_trace()
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('<meta name="arena-ui-generation" content="008">', page)
        self.assertIn("Close this dialog to return to the map and movement controls.", page)
        self.assertIn("const traceEnabled=true", page)
        # This source-level contract verifies that shipped handlers correlate a
        # fire-and-forget client event with the destination/advance request.
        self.assertIn("traceUI('canvas_hex_selected',cell)", page)
        self.assertIn("traceUI('canvas_click_received')", page)
        self.assertIn("traceUI('destination_request_queued'", page)
        self.assertIn("traceUI('destination_request_accepted',cell)", page)
        self.assertIn("traceUI('page_script_ready')", page)
        self.assertIn("traceUI('page_script_error')", page)
        self.assertNotIn("$('renameEntity').onclick", page)
        self.assertNotIn("$('pickup').onclick", page)
        self.assertIn("Close any open dialog to return to the map.", page)
        self.assertIn("req('/api/generated/destination'", page)
        self.assertIn("traceUI('advance_clicked')", page)
        self.assertIn("req('/api/generated/advance',{seconds:1},sequence)", page)
        self.assertIn("/api/generated/rename-entity", page)
        self.assertIn("const sequence=traceUI('rename_entity_clicked')", page)
        self.assertIn("b.textContent=", page)
        self.assertNotIn("innerHTML", page)
        self.assertIn("Already at that hex center", page)

        trace_empty = self.session.public_view()
        self.request("/api/generated/trace", {"seq": 1, "event": "generate_clicked"})
        self.request("/api/generated/trace", {
            "seq": 2, "event": "rate_selected", "rate": "walk"})
        self.request("/api/generated/trace", {
            "seq": 3, "event": "facing_policy_selected", "facing_policy": "turn"})
        self.assertEqual(self.session.public_view(), trace_empty)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"},
            headers={"X-Arena-Client-Seq": "4"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        hidden = candidate.participants[1].native.being
        start = player.get_position()
        rng_state = self.session._rng_cursor.state
        self.assertNotIn(hidden.id, json.dumps(generated))
        self.assertNotIn("client_seq", json.dumps(generated))
        self.assertNotIn("source_record", json.dumps(generated))

        # Clicking the occupied center is a real accepted no-op, not an active
        # plan; the browser now says so and keeps Advance disabled.
        current_cell = generated["player"]["cell"]
        self.request("/api/generated/trace", {
            "seq": 5, "event": "canvas_hex_selected", **current_cell})
        status, no_op = self.request("/api/generated/destination", {
            **current_cell, "rate": "walk", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(no_op["movement_outcome"], "already_at_destination")
        self.assertFalse(no_op["advance_available"])
        self.request("/api/generated/trace", {"seq": 6, "event": "advance_clicked"})
        status, refused = self.request("/api/generated/advance", {"seconds": 1},
                                       headers={"X-Arena-Client-Seq": "6"})
        self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, 0)

        for payload in (
            {"column": 99, "row": 0, "rate": "walk", "facing_policy": "turn"},
            {"column": "1", "row": 0, "rate": "walk", "facing_policy": "turn"},
        ):
            status, _ = self.request("/api/generated/destination", payload)
            self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, 0)
        self.assertIsNone(self.session.public_view()["movement_plan"])
        self.assertEqual(self.session._rng_cursor.state, rng_state)

        # Concurrent repeated clicks serialize under the session lock. Each
        # accepted destination is a plan replacement, not an interval commit.
        current = current_cell
        alternatives = [(column, row) for column in range(5) for row in range(5)
                        if (column, row) != (current["column"], current["row"])][:8]
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(lambda cell: self.request(
                "/api/generated/destination", {"column": cell[0], "row": cell[1],
                 "rate": "walk", "facing_policy": "turn"}), alternatives))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(candidate.encounter.time, 0)
        plan = self.session.public_view()["movement_plan"]
        self.assertIsNotNone(plan)
        destination_cell = plan["destination_cell"]
        target = candidate.arena_map.layout.center_position(
            HexAddress(destination_cell["column"], destination_cell["row"]), z=start.z)

        # Injected native failure must log a rollback and leave time/position,
        # plan, ChoiceBook, and RNG untouched.
        from unittest.mock import patch
        before_view = self.session.public_view()
        before_choices = dict(candidate.encounter._choice_book._choices)
        self.request("/api/generated/trace", {"seq": 15, "event": "advance_clicked"})
        with patch.object(candidate.encounter, "step", side_effect=RuntimeError("injected step fault")):
            status, _ = self.request("/api/generated/advance", {"seconds": 1},
                                     headers={"X-Arena-Client-Seq": "15"})
        self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(player.get_position(), start)
        self.assertEqual(self.session.public_view(), before_view)
        self.assertEqual(candidate.encounter._choice_book._choices, before_choices)
        self.assertEqual(self.session._rng_cursor.state, rng_state)

        self.request("/api/generated/trace", {"seq": 16, "event": "advance_clicked"})
        status, moving = self.request("/api/generated/advance", {"seconds": 1},
                                      headers={"X-Arena-Client-Seq": "16"})
        self.assertEqual(status, 200)
        self.assertEqual(moving["time_seconds"], 1)
        self.assertNotEqual(player.get_position(), start)
        self.assertNotIn(hidden.id, json.dumps(moving))
        while self.session.public_view()["movement_plan"] is not None:
            status, view = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            self.assertNotIn(hidden.id, json.dumps(view))
        self.assertEqual(player.get_position(), truncate_position(target))
        self.assertIn("event=canvas_hex_selected", stream.getvalue())
        self.assertIn("event=rate_selected rate=walk", stream.getvalue())
        self.assertIn("action=generate status=accepted http=200 xp=0 map=5x5", stream.getvalue())
        self.assertIn("plan=already_at_destination", stream.getvalue())
        self.assertIn("movement=no_plan", stream.getvalue())
        self.assertIn("status=rolled_back", stream.getvalue())
        self.assertIn("reason=RuntimeError", stream.getvalue())
        self.assertIn("action=advance status=accepted http=200", stream.getvalue())
        self.assertIn("movement=arrival", stream.getvalue())
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        for forbidden in (hidden.id, hidden.name, "source_record", "root_seed"):
            self.assertNotIn(forbidden, stream.getvalue())

    def test_map_click_trace_is_fixed_schema_and_contains_no_entity_identity(self):
        stream = self.enable_trace()
        self.assertIn('<meta name="arena-ui-generation" content="008">',
                      self.request("/")[1])
        events = [
            {"event": "page_script_ready"},
            {"event": "canvas_click_received"},
            {"event": "canvas_modal_blocked"},
            {"event": "canvas_entity_marker_hit", "entity_category": "object"},
            {"event": "canvas_marker_missed"},
            {"event": "canvas_hex_selected", "column": 3, "row": 2},
            {"event": "melee_strike_clicked"},
            {"event": "destination_request_queued", "column": 3, "row": 2,
             "rate": "walk", "facing_policy": "turn"},
            {"event": "destination_request_accepted", "column": 3, "row": 2},
            {"event": "page_script_error"},
        ]
        for sequence, details in enumerate(events, start=1):
            self.assertEqual(self.request("/api/generated/trace", {
                "seq": sequence, **details})[0], 200)
        self.assertEqual(self.request("/api/generated/trace", {
            "seq": len(events) + 1, "event": "canvas_entity_marker_hit",
            "entity_category": "object", "handle": "private-handle"})[0], 409)
        output = stream.getvalue()
        for event in ("page_script_ready", "canvas_click_received", "canvas_modal_blocked",
                      "canvas_entity_marker_hit entity_category=object", "canvas_marker_missed",
                      "melee_strike_clicked",
                      "canvas_hex_selected cell=(3,2)",
                      "destination_request_queued cell=(3,2) rate=walk policy=turn",
                      "destination_request_accepted cell=(3,2)", "page_script_error"):
            self.assertIn(event, output)
        self.assertNotIn("private-handle", output)

    def test_shipped_option_handlers_replace_active_plan_and_serialize_advance(self):
        _, page = self.request("/")
        self.assertIn("function serializeMutation(operation)", page)
        self.assertIn("function optionChanged(event,detail)", page)
        self.assertIn("updatePlanFromSelection(sequence,rate,policy)", page)
        self.assertIn("server accepted ${plan.rate}/${plan.facing_policy}", page)
        self.assertIn("selected ${selectedRate}/${selectedPolicy}", page)
        self.assertIn("Movement plan accepted: ${state.movement_plan.rate}/${state.movement_plan.facing_policy}", page)
        self.assertIn("await serializeMutation(async()=>{\n    try{\n      const state=await req('/api/generated/destination'", page)
        self.assertIn("serializeMutation(async()=>{if(planUpdateFailure)", page)
        self.assertIn("req('/api/generated/advance',{seconds:1},sequence)", page)

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("swift"),
                         "JavaScriptCore via Swift is available on macOS only")
    def test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance(self):
        stream = self.enable_trace()
        loadout_profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        # This JS handler exercise needs one reachable ground pickup. Duplicate
        # Dagger instances create legitimate uncertain route cells unrelated to
        # the handler's option-change ordering.
        loadout_profile["categories"]["weapon"]["count"] = 1
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 1,
            trace_ui=True, trace_stream=stream, ground_loadout_profile=loadout_profile)
        _, page = self.request("/")
        self.assertNotIn('id="characterPanel"', page)
        self.assertIn('id="entityDialog"', page)
        self.assertNotIn('id="characterButton"', page)
        self.assertIn('function openCharacterPopup(trigger)', page)
        state = self.session.generate({
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "opponent_strategy": "none"})
        player = self.session.active_candidate.participants[0].native.being
        player.current.body_parts["right hand"] = None
        state = self.session.public_view()
        object_views = [row for row in state["entities"]
                        if row["category"] == "object" and row["type"] == "Dagger"]
        selected = None
        route_refusals = []
        for candidate_object in object_views:
            candidate_target = HexAddress(candidate_object["cell"]["column"],
                                          candidate_object["cell"]["row"])
            try:
                self.session.choose_destination({"column": candidate_target.column,
                    "row": candidate_target.row, "rate": "sprint", "facing_policy": "turn"})
            except ArenaBrowserRequestError as exc:
                route_refusals.append(str(exc))
                continue
            selected = candidate_object, candidate_target
            break
        self.assertIsNotNone(selected, route_refusals)
        object_view, target = selected
        self.session.rename_entity({"handle": object_view["handle"], "name": "Renamed Dagger"})
        for _ in range(100):
            if self.session.public_view()["movement_plan"] is None:
                break
            self.session.advance_one_second()
        self.assertIsNone(self.session.public_view()["movement_plan"])
        self.session.inspect_entity({"handle": object_view["handle"]})
        self.session.choose_pickup({"handle": object_view["handle"]})
        self.session.advance_one_second()
        picked_up_view = self.session.public_view()
        self.assertEqual(picked_up_view["character"]["inventory"]["items"][0]["name"],
                         "Renamed Dagger")

        with tempfile.TemporaryDirectory(prefix="arena-browser-js-") as temp:
            page_path = Path(temp) / "page.html"
            state_path = Path(temp) / "initial-state.json"
            cell_path = Path(temp) / "target-cell.json"
            picked_up_path = Path(temp) / "picked-up-view.json"
            refusal_path = Path(temp) / "movement-refusal.json"
            page_path.write_text(page, encoding="utf-8")
            state_path.write_text(json.dumps(state), encoding="utf-8")
            cell_path.write_text(json.dumps({"column": target.column, "row": target.row}),
                                 encoding="utf-8")
            picked_up_path.write_text(json.dumps(picked_up_view), encoding="utf-8")
            refusal_path.write_text(json.dumps({"error": "Your Being is at 0 HP or below and cannot take voluntary movement under the adopted rules. No Encounter time or position changed; your destination plan remains selected.",
                "movement_refusal": {"category": "actor_unable_to_move", "message": "Your Being is at 0 HP or below and cannot take voluntary movement under the adopted rules. No Encounter time or position changed; your destination plan remains selected."}}), encoding="utf-8")
            module_cache = Path(tempfile.gettempdir()) / "universe-arena-jsc-module-cache"
            module_cache.mkdir(parents=True, exist_ok=True)
            harness = ROOT / "tests" / "arena_browser_js_harness.swift"
            run = subprocess.run(
                [shutil.which("swift"), "-module-cache-path", str(module_cache), str(harness),
                 str(page_path), str(state_path), str(cell_path), str(picked_up_path),
                 str(refusal_path)],
                check=False, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        movement_requests = [call for call in result["calls"]
                             if call["path"] in ("/api/generated/destination", "/api/generated/advance")]
        self.assertEqual([call["path"] for call in movement_requests], [
            "/api/generated/advance",
            "/api/generated/destination", "/api/generated/destination",
            "/api/generated/destination", "/api/generated/advance",
            "/api/generated/advance",
            "/api/generated/advance", "/api/generated/advance",
            "/api/generated/destination",
            "/api/generated/destination", "/api/generated/destination",
            "/api/generated/destination",
            "/api/generated/advance", "/api/generated/destination",
            "/api/generated/advance"])
        destination_requests = [call for call in movement_requests
                                if call["path"] == "/api/generated/destination"]
        self.assertEqual([call["body"]["rate"] for call in destination_requests],
                         ["sprint", "walk", "sprint", "walk", "walk", "walk", "sprint", "sprint"])
        self.assertIn("Dagger", result["entityDetails"])
        self.assertIn("Pick up", result["pickupStatus"])
        self.assertIn("/api/generated/inspect", [call["path"] for call in result["calls"]])
        self.assertIn("/api/generated/run", [call["path"] for call in result["calls"]])
        self.assertIn("/api/generated/pickup", [call["path"] for call in result["calls"]])
        draw_calls = [call for call in result["calls"]
                      if call["path"] == "/api/generated/ready-weapon"]
        self.assertEqual(len(draw_calls), 1)
        self.assertEqual(draw_calls[0]["body"]["hand"], "right hand")
        self.assertNotIn("native_id", json.dumps(draw_calls[0]["body"]))
        self.assertIn("/api/generated/rename-entity", [call["path"] for call in result["calls"]])
        rename_call = next(call for call in result["calls"] if call["path"] == "/api/generated/rename-entity")
        self.assertEqual(rename_call["body"]["name"], "Renamed Dagger")
        self.assertNotIn("native_id", json.dumps(rename_call["body"]))
        self.assertEqual(result["finalEntity"]["name"], "Renamed Dagger")
        self.assertEqual(result["finalEntity"]["present_state"], "carried")
        self.assertIn("Renamed Dagger", result["entityDetails"])
        self.assertIn("carried", result["entityDetails"])
        self.assertIn("carried; not readied", " ".join(result["characterInventory"]))
        self.assertEqual(result["refusalCategory"], "actor_unable_to_move")
        self.assertIn("cannot take voluntary movement", result["error"])
        inventory_output = " ".join(result["characterInventory"])
        self.assertIn("Renamed Dagger", inventory_output)
        self.assertIn("carried; not readied", inventory_output)
        character_text = json.dumps(result["characterSummary"])
        for label in ("Fitness", "Current total native XP", "Hit points", "Earned practice XP",
                      "Position and movement", "Age:", "Class XP"):
            self.assertIn(label, character_text)
        self.assertIn("Represented carried weight", character_text)
        self.assertEqual([call["body"]["facing_policy"] for call in destination_requests],
                         ["turn", "turn", "turn", "turn", "maintain", "turn", "turn", "turn"])
        for call in destination_requests[:-1]:
            self.assertEqual(call["body"]["column"], target.column)
            self.assertEqual(call["body"]["row"], target.row)
        self.assertGreater(int(movement_requests[4]["headers"]["X-Arena-Client-Seq"]),
                           int(destination_requests[2]["headers"]["X-Arena-Client-Seq"]))
        self.assertLess(result["calls"].index(destination_requests[2]),
                        result["calls"].index(movement_requests[4]))
        self.assertEqual(result["plan"]["rate"], "sprint")
        self.assertIn("server accepted sprint/turn", result["status"])
        self.assertEqual(result["time"], 1)
        self.assertEqual(result["freshMovement"]["time"], 1)
        self.assertIsNone(result["freshMovement"]["playerAction"])
        self.assertNotEqual(result["freshMovement"]["position"], result["freshMovement"]["start"])
        self.assertEqual(result["freshMovement"]["runCount"],
                         result["freshMovement"]["runCountBefore"])
        trace_events = [call["body"]["event"] for call in result["calls"]
                        if call["path"] == "/api/generated/trace"]
        for event in ("page_script_ready", "canvas_click_received", "canvas_player_marker_hit",
                      "canvas_entity_marker_hit", "destination_request_queued",
                      "destination_request_accepted"):
            self.assertIn(event, trace_events)
        self.assertIn("cannot take voluntary movement", result["error"])
        self.assertTrue(any(label.lower().startswith("small shield · ground")
                            for label in result["entityLabels"]))
        self.assertFalse(any("small shield · small shield" in label.lower()
                             for label in result["entityLabels"]))

    def test_destination_then_sprint_updates_accepted_plan_before_native_step(self):
        stream = self.enable_trace()
        self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        being = player.native.being
        start = being.get_position()
        layout = candidate.arena_map.layout
        from movement_intent import _movement_hexes
        origin = layout.cell_at_position(start)
        occupied = {layout.cell_at_position(part.native.being.get_position())
                    for part in candidate.participants if part.native.being.id != being.id}
        occupied.update(layout.cell_at_position(row.position)
                        for row in candidate.ground_objects)
        valid_destinations = []
        for cell in layout.addresses():
            destination = layout.center_position(cell, z=start.z)
            try:
                route = _movement_hexes(start, destination, layout) - {origin}
            except Exception:
                continue
            if not route.intersection(occupied):
                valid_destinations.append(cell)
        address = max(valid_destinations,
            key=lambda cell: math.dist(start.as_tuple(),
                layout.center_position(cell, z=start.z).as_tuple()))
        before_history = dict(candidate.universe.event_history)
        before_choices = dict(encounter._choice_book._choices)
        before_awareness = (encounter.aware_beings(being.id),
                            encounter.aware_beings(hidden.native.being.id))
        before_rng = self.session._rng_cursor.state

        self.request("/api/generated/trace", {"seq": 1, "event": "canvas_hex_selected",
                     "column": address.column, "row": address.row})
        status, walk = self.request("/api/generated/destination", {
            "column": address.column, "row": address.row,
            "rate": "walk", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "1"})
        self.assertEqual(status, 200)
        self.assertEqual(walk["movement_plan"]["rate"], "walk")
        self.request("/api/generated/trace", {"seq": 2, "event": "rate_selected", "rate": "sprint"})
        status, sprint = self.request("/api/generated/destination", {
            **walk["movement_plan"]["destination_cell"],
            "rate": "sprint", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "2"})
        self.assertEqual(status, 200)
        self.assertEqual(sprint["movement_plan"]["rate"], "sprint")
        self.assertEqual(sprint["movement_plan"]["destination_cell"],
                         {"column": address.column, "row": address.row})
        self.assertEqual(sprint["time_seconds"], 0)
        self.assertEqual(being.get_position(), start)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter._choice_book._choices, before_choices)
        self.assertEqual(before_awareness, (encounter.aware_beings(being.id),
                                           encounter.aware_beings(hidden.native.being.id)))
        self.assertEqual(self.session._rng_cursor.state, before_rng)
        self.assertNotIn(hidden.native.being.id, json.dumps(sprint))

        self.request("/api/generated/trace", {"seq": 3, "event": "advance_clicked"})
        status, advanced = self.request("/api/generated/advance", {"seconds": 1},
                                        headers={"X-Arena-Client-Seq": "3"})
        self.assertEqual(status, 200)
        self.assertEqual(advanced["time_seconds"], 1)
        self.assertGreater(math.dist(start.as_tuple(), being.get_position().as_tuple()), 0.9144)
        self.assertIn("event=rate_selected rate=sprint", stream.getvalue())
        self.assertIn("client_seq=2 action=destination status=accepted http=200", stream.getvalue())
        self.assertIn("rate=sprint policy=turn plan=accepted", stream.getvalue())
        self.assertIn("status=committed time=0->1", stream.getvalue())
        self.assertIn("rate=sprint,policy=turn", stream.getvalue())
        self.assertNotIn(hidden.native.being.id, stream.getvalue())
        self.assertNotIn("seed=", stream.getvalue())

    def test_geometryless_ground_object_intermediate_passage_fails_closed_without_state_leak(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 1,
            ground_item_descriptions=[{"source_item_id": "path-test-dagger",
                "category": "weapon", "native_type_key": "Dagger", "quantity": 1,
                "ordinary": True, "magical": False, "mechanics": None,
                "origin": "movement-test.v1"}])
        state = self.session.generate({"starting_experience": "10000",
            "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        placement = next(row for row in candidate.ground_objects
                         if row.native_type_key == "Dagger")
        target = next(row for row in state["entities"]
                      if row["type"] == "Dagger" and row["category"] == "object")
        self.assertNotEqual(candidate.arena_map.layout.cell_at_position(player.get_position()),
                            HexAddress(placement.column, placement.row))
        before = (player.get_position(), candidate.encounter.time,
            self.session._rng_cursor.state, dict(candidate.universe.event_history),
            dict(candidate.encounter._choice_book._choices), placement.native_object_id)
        destination = HexAddress(4, 2)
        from movement_intent import _movement_hexes
        route = _movement_hexes(player.get_position(),
            candidate.arena_map.layout.center_position(destination,
                z=player.get_position().z), candidate.arena_map.layout)
        self.assertIn(HexAddress(placement.column, placement.row), route)
        self.assertNotEqual(destination, HexAddress(placement.column, placement.row))
        plan = self.session.choose_destination({"column": destination.column,
            "row": destination.row, "rate": "sprint", "facing_policy": "turn"})
        self.assertIsNotNone(plan["movement_plan"])
        with self.assertRaises(ArenaBrowserRequestError) as refused:
            self.session.advance_one_second()
        self.assertEqual(refused.exception.movement_refusal["category"],
                         "movement_prerequisite_not_met")
        self.assertNotIn(placement.native_object_id, str(refused.exception))
        self.assertEqual(before[:5], (player.get_position(), candidate.encounter.time,
            self.session._rng_cursor.state, dict(candidate.universe.event_history),
            dict(candidate.encounter._choice_book._choices)))
        self.assertEqual(self.session.public_view()["movement_plan"]["destination_cell"],
                         {"column": destination.column, "row": destination.row})
        self.assertIsNone(candidate.universe.get_object_by_id(
            placement.native_object_id).parent_container_id)
        self.assertNotIn(candidate.participants[0].native.being.id, json.dumps(target))

    def test_sprint_before_destination_and_rapid_policy_rate_edits_use_latest_plan(self):
        stream = self.enable_trace()
        self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        being = candidate.participants[0].native.being
        start = being.get_position()
        layout = candidate.arena_map.layout
        address = max(
            (HexAddress(column, row)
             for column in range(candidate.arena_map.width_cells)
             for row in range(candidate.arena_map.height_cells)),
            key=lambda cell: math.dist(start.as_tuple(), layout.center_position(cell, z=start.z).as_tuple()))
        self.request("/api/generated/trace", {"seq": 1, "event": "rate_selected", "rate": "sprint"})
        self.request("/api/generated/trace", {"seq": 2, "event": "facing_policy_selected",
                     "facing_policy": "turn"})
        status, selected = self.request("/api/generated/destination", {
            "column": address.column, "row": address.row,
            "rate": "sprint", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "3"})
        self.assertEqual(status, 200)
        self.assertEqual(selected["movement_plan"]["rate"], "sprint")

        # Serialized selector edits followed immediately by Advance represent
        # the browser queue's required causal order.
        self.request("/api/generated/trace", {"seq": 4, "event": "facing_policy_selected",
                     "facing_policy": "maintain"})
        status, maintained = self.request("/api/generated/destination", {
            **selected["movement_plan"]["destination_cell"],
            "rate": "sprint", "facing_policy": "maintain"},
            headers={"X-Arena-Client-Seq": "4"})
        self.assertEqual(status, 200)
        self.assertEqual(maintained["movement_plan"]["facing_policy"], "maintain")
        self.request("/api/generated/trace", {"seq": 5, "event": "rate_selected", "rate": "jog"})
        status, jog = self.request("/api/generated/destination", {
            **maintained["movement_plan"]["destination_cell"],
            "rate": "jog", "facing_policy": "maintain"},
            headers={"X-Arena-Client-Seq": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(jog["movement_plan"]["rate"], "jog")
        self.request("/api/generated/trace", {"seq": 6, "event": "rate_selected", "rate": "sprint"})
        status, sprint = self.request("/api/generated/destination", {
            **jog["movement_plan"]["destination_cell"],
            "rate": "sprint", "facing_policy": "maintain"},
            headers={"X-Arena-Client-Seq": "6"})
        self.assertEqual(status, 200)
        self.assertEqual(sprint["movement_plan"]["rate"], "sprint")
        self.assertEqual(sprint["movement_plan"]["facing_policy"], "maintain")
        self.request("/api/generated/trace", {"seq": 7, "event": "advance_clicked"})
        status, advanced = self.request("/api/generated/advance", {"seconds": 1},
                                        headers={"X-Arena-Client-Seq": "7"})
        self.assertEqual(status, 200)
        self.assertEqual(advanced["time_seconds"], 1)
        self.assertIn("rate=sprint,policy=maintain", stream.getvalue())

    def test_invalid_rate_update_keeps_previous_server_plan(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        start_cell = candidate.arena_map.layout.cell_at_position(
            candidate.participants[0].native.being.get_position())
        destination = next(HexAddress(column, row)
            for column in range(candidate.arena_map.width_cells)
            for row in range(candidate.arena_map.height_cells)
            if HexAddress(column, row) != start_cell)
        _, accepted = self.request("/api/generated/destination", {
            "column": destination.column, "row": destination.row,
            "rate": "walk", "facing_policy": "turn"})
        before = self.session.public_view()
        status, _ = self.request("/api/generated/destination", {
            "column": destination.column, "row": destination.row,
            "rate": "sprint-invalid", "facing_policy": "maintain"})
        self.assertEqual(status, 409)
        after = self.session.public_view()
        self.assertEqual(after, before)
        self.assertEqual(after["movement_plan"]["rate"], accepted["movement_plan"]["rate"])
        self.assertEqual(after["movement_plan"]["facing_policy"],
                         accepted["movement_plan"]["facing_policy"])

    def test_trace_schema_rejects_arbitrary_fields_and_client_sequence_is_bounded(self):
        stream = self.enable_trace()
        before = self.session.public_view()
        for payload in (
            {"seq": 1, "event": "rate_selected", "rate": "walk", "name": "private"},
            {"seq": 2**40, "event": "advance_clicked"},
            {"seq": 2, "event": "rate_selected", "rate": "private-value"},
        ):
            status, _ = self.request("/api/generated/trace", payload)
            self.assertEqual(status, 409)
        self.assertEqual(self.session.public_view(), before)
        self.assertEqual(stream.getvalue(), "")

    def test_trace_diagnostic_route_refuses_nonlocal_origin(self):
        stream = self.enable_trace()
        status, _ = self.request("/api/generated/trace", {
            "seq": 1, "event": "advance_clicked"},
            headers={"Origin": "https://example.invalid"})
        self.assertEqual(status, 404)
        self.assertEqual(stream.getvalue(), "")

    def test_client_trace_has_a_per_second_rate_limit(self):
        import io
        from arena_ui_trace import ArenaUITerminalTrace
        now = [0.0]
        trace = ArenaUITerminalTrace(True, stream=io.StringIO(), clock=lambda: now[0])
        for seq in range(1, 31):
            trace.client_event({"seq": seq, "event": "advance_clicked"})
        with self.assertRaisesRegex(ValueError, "rate limit"):
            trace.client_event({"seq": 31, "event": "advance_clicked"})
        now[0] = 1.0
        self.assertEqual(trace.client_event({"seq": 32, "event": "advance_clicked"}),
                         {"accepted": True})

    def test_character_sheet_trace_event_contains_no_private_details(self):
        stream = self.enable_trace()
        status, result = self.request("/api/generated/trace", {
            "seq": 1, "event": "character_sheet_opened"})
        self.assertEqual(status, 200)
        self.assertEqual(result, {"accepted": True})
        self.assertIn("event=character_sheet_opened", stream.getvalue())
        self.assertNotIn("name", stream.getvalue())

    def test_generate_returns_only_player_allowlist_and_rename_preserves_native_identity(self):
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(state["state"], "active")
        self.assertEqual(state["time_seconds"], 0)
        self.assertEqual(state["map"]["width_cells"], 5)
        self.assertEqual(state["map"]["height_cells"], 5)
        self.assertEqual(state["map"]["orientation"], "flat_top_odd_column_north_offset")
        self.assertEqual(state["map"]["cell_size_meters"], 0.9144)
        self.assertEqual(state["map"]["column_row_ranges"], None)
        self.assertEqual(state["map"]["world_premise"], {
            "terrain": "Plains", "route": "Road", "terrain_multiplier": 1.0,
            "hampered_multiplier": 1.0, "unobstructed": True,
            "collision_adjudicated": False})
        self.assertTrue(state["movement_available"])
        self.assertFalse(state["spot_available"])
        candidate = self.session.active_candidate
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(len(candidate.participants), 2)
        self.assertNotEqual(candidate.participants[0].native.being.id,
                            candidate.participants[1].native.being.id)
        player_participant, other_participant = candidate.participants
        self.assertEqual(state["player"]["hex_facing"], player_participant.native.being.hex_facing)
        self.assertEqual(state["player"]["posture"], "standing")
        self.assertEqual(state["player"]["posture_source"],
                         "arena.initial-posture.v1/scenario")
        self.assertEqual(player_participant.native.being.posture, "standing")
        self.assertEqual(other_participant.native.being.posture, "standing")
        self.assertTrue(0 <= state["player"]["hex_facing"] < 12)
        self.assertEqual(state["player"]["cell"], {
            "column": player_participant.placement.column,
            "row": player_participant.placement.row})
        self.assertEqual(state["player"]["position_meters"], {
            "x": player_participant.native.being.get_position().x,
            "y": player_participant.native.being.get_position().y,
            "z": player_participant.native.being.get_position().z})
        self.assertEqual([p.native.being.get_experience() for p in candidate.participants], [0, 0])
        def exposed_keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield str(key).casefold()
                    yield from exposed_keys(child)
            elif isinstance(value, (tuple, list)):
                for child in value:
                    yield from exposed_keys(child)
        encoded = json.dumps(state).lower()
        for forbidden in ("source_sha256", "source_record", "native_id", "awareness",
                          "target_id", "action_id", "participants"):
            self.assertNotIn(forbidden, set(exposed_keys(state)))
        self.assertEqual(state["character"]["identity"]["class_levels"],
                         state["character"]["experience"]["class_allocation"])
        self.assertEqual(state["character"]["experience"]["class_allocation"][0]["id"], 1)
        self.assertEqual(state["character"]["experience"]["total"], 0)
        self.assertNotIn(other_participant.native.being.id, encoded)
        self.assertEqual(len(state["entities"]), 1)
        self.assertEqual(state["entities"][0]["category"], "being")
        self.assertEqual(state["entities"][0]["type"], "Being")
        # npcgen can produce duplicate names for the independently generated pair.
        # The Arena distinguishes the opponent in its player-facing projection only.
        self.assertEqual(state["entities"][0]["name"],
                         f"{other_participant.native.being.name} (Arena)")
        hidden_position = other_participant.native.being.get_position()
        self.assertEqual(state["entities"][0]["position_meters"], {
            "x": hidden_position.x, "y": hidden_position.y, "z": hidden_position.z})
        ledgers = [participant.native.being._arena_perception_ledger
                   for participant in candidate.participants]
        self.assertIsNot(ledgers[0], ledgers[1])
        self.assertIsNot(ledgers[0]._current, ledgers[1]._current)
        self.assertIsNot(ledgers[0].history[0], ledgers[1].history[0])
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(candidate.encounter._choice_book._choices, {})
        self.assertEqual(set(state["player"]),
                         {"name", "size_category", "hex_facing", "posture", "posture_source",
                          "cell", "position_meters"})
        hidden_position_payload = json.dumps({"x": hidden_position.x,
                                              "y": hidden_position.y,
                                              "z": hidden_position.z})
        self.assertIn(hidden_position_payload, encoded)
        _, generated_page = self.request("/")
        self.assertIn("movementStatus", generated_page)
        self.assertIn("s.player.hex_facing*Math.PI/6", generated_page)
        player = candidate.participants[0].native.being
        native_id, source_bytes = player.id, candidate.participants[0].native.source_record_bytes

        status, renamed = self.request("/api/generated/player-name", {"name": "Mira"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed["player"]["name"], "Mira")
        self.assertEqual(player.id, native_id)
        self.assertEqual(player.name, "Mira")
        self.assertEqual(candidate.participants[0].native.source_record_bytes, source_bytes)
        status, named = self.request("/api/generated/encounter-name", {"name": "Trial"})
        self.assertEqual(status, 200)
        self.assertEqual(named["encounter_name"], "Trial")
        self.assertEqual(candidate.encounter.name, "Trial")

    def test_http_visible_object_selection_pickup_and_custody_use_native_action(self):
        trace_stream = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
            trace_ui=True, trace_stream=trace_stream,
            ground_item_descriptions=[{"source_item_id": "http-dagger", "category": "weapon",
                "native_type_key": "Dagger", "quantity": 1, "ordinary": True,
                "magical": False, "mechanics": None, "origin": "http-test.v1"}])
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        catalog = state["action_catalog"]
        action_entries = {row["name"]: row for row in catalog["entries"]}
        with (ROOT / "src/config/actions.tsv").open(encoding="utf-8") as source:
            source_names = {line.split("\t", 1)[0] for line in source.read().splitlines()[1:]}
        self.assertTrue((source_names - {"parry (armed)", "parry (unarmed)"}).issubset(action_entries))
        self.assertIn("Parry", action_entries)
        self.assertEqual(action_entries["Run"]["status"], "available")
        self.assertEqual(action_entries["Spot"]["status"], "unavailable")
        self.assertEqual(action_entries["Pick up"]["status"], "unavailable")
        self.assertIn("perceived ground Object", action_entries["Pick up"]["reason"])
        self.assertEqual(action_entries["ready weapon"]["status"], "unavailable")
        self.assertIn("carried Weapon", action_entries["ready weapon"]["reason"])
        self.assertEqual(action_entries["grab object"]["status"], "unavailable")
        self.assertIn("Select a currently perceived weapon held by an opposing Being",
                      action_entries["grab object"]["reason"])
        target = next(row for row in state["entities"] if row["type"] == "Dagger")
        candidate = self.session.active_candidate
        placement = next(row for row in candidate.ground_objects if row.native_type_key == "Dagger")
        native = candidate.universe.get_object_by_id(placement.native_object_id)
        player = candidate.participants[0].native.being
        # Explicit test-world native hand state; generated race templates do
        # not currently define hands and Arena initialization does not add them.
        player.current.body_parts["right hand"] = None
        character = state["character"]
        self.assertEqual(character["identity"]["display_name"], state["player"]["name"])
        self.assertEqual(character["identity"]["native_type"], player.current.obj_type)
        self.assertEqual(character["identity"]["race"], player.current.race)
        self.assertIsInstance(character["identity"]["age"], float)
        self.assertTrue(character["identity"]["class_levels"])
        self.assertEqual(character["identity"]["stature_inches"], player.current.length)
        self.assertEqual(character["identity"]["body_weight_pounds"], player.current.weight)
        self.assertEqual(character["experience"]["total"], player.get_experience())
        self.assertEqual(character["condition"]["hit_points_current"], player.get_hit_points())
        self.assertIsNone(character["condition"]["hit_points_maximum"])
        self.assertEqual(character["movement"]["position_meters"], state["player"]["position_meters"])
        self.assertEqual(character["inventory"]["status"], "available")
        self.assertEqual(character["inventory"]["items"], [])
        self.assertEqual(character["inventory"]["carried_weight_pounds"], 0.0)
        ledgers = tuple(participant.native.being._arena_perception_ledger
                        for participant in candidate.participants)
        evidence_before = tuple((dict(ledger._current), tuple(ledger.history)) for ledger in ledgers)
        rng_before, time_before = self.session._rng_cursor.state, candidate.encounter.time
        before_choices = dict(candidate.encounter._choice_book._choices)
        native_name, native_id = native.name, native.id
        self.assertNotIn(native.id, json.dumps(state))
        self.assertEqual(self.session.public_view(), state)
        self.assertEqual((candidate.encounter.time, self.session._rng_cursor.state),
                         (time_before, rng_before))
        self.assertEqual(candidate.encounter._choice_book._choices, before_choices)
        self.assertEqual(self.request("/api/generated/action", {"action": "ready weapon"})[0], 404)
        self.assertEqual(self.session.public_view(), state)
        self.assertEqual(self.request("/api/generated/pickup", {"handle": target["handle"]})[0], 409)
        self.assertEqual(self.session.public_view(), state)
        self.request("/api/generated/trace", {"seq": 1, "event": "entity_selected"})
        status, inspected = self.request("/api/generated/inspect", {"handle": target["handle"]},
                                         {"X-Arena-Client-Seq": "1"})
        self.assertEqual(status, 200)
        self.assertEqual(inspected["selected_entity"]["name"], "Dagger")
        self.assertEqual(next(row for row in inspected["action_catalog"]["entries"]
                              if row["name"] == "Pick up")["status"], "unavailable")
        self.request("/api/generated/trace", {"seq": 2, "event": "rename_entity_clicked"})
        status, renamed = self.request("/api/generated/rename-entity",
            {"handle": target["handle"], "name": "My Dagger"}, {"X-Arena-Client-Seq": "2"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed["selected_entity"]["name"], "My Dagger")
        self.assertEqual(renamed["character"]["inventory"]["items"], [])
        self.assertEqual(native.id, native_id)
        self.assertEqual(native.name, native_name)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        for ledger, before in zip(ledgers, evidence_before):
            self.assertEqual(ledger._current, before[0])
            self.assertEqual(tuple(ledger.history), before[1])
        self.assertEqual(candidate.encounter._choice_book._choices, {})
        cell = target["cell"]
        if player.get_position() != self.session.active_candidate.arena_map.layout.center_position(
                HexAddress(cell["column"], cell["row"])):
            status, moving = self.request("/api/generated/destination", {
                **cell, "rate": "sprint", "facing_policy": "turn"})
            self.assertEqual(status, 200)
            for _ in range(100):
                if self.session.public_view()["movement_plan"] is None:
                    break
                status, moving = self.request("/api/generated/advance", {"seconds": 1})
                self.assertEqual(status, 200)
                self.assertEqual(moving["character"]["movement"]["position_meters"],
                                 moving["player"]["position_meters"])
        expected_destination = self.session.active_candidate.arena_map.layout.center_position(
            HexAddress(cell["column"], cell["row"]))
        self.assertEqual(player.get_position(), truncate_position(expected_destination))
        if not self.session.active_candidate.encounter.initiated:
            self.assertEqual(self.request("/api/generated/run", {})[0], 200)
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        available_pickup = self.session.public_view()["action_catalog"]["entries"]
        self.assertEqual(next(row for row in available_pickup if row["name"] == "Pick up")["status"],
                         "available")
        self.assertTrue(next(row for row in self.session.public_view()["entities"]
                             if row["handle"] == target["handle"])["pickup_available"])
        self.request("/api/generated/trace", {"seq": 3, "event": "pickup_clicked"})
        status, pickup = self.request("/api/generated/pickup", {"handle": target["handle"]},
                                      {"X-Arena-Client-Seq": "3"})
        self.assertEqual(status, 200)
        self.assertEqual(pickup["pickup_action"]["status"], "executing")
        pending_catalog = pickup["action_catalog"]["entries"]
        self.assertEqual(next(row for row in pending_catalog if row["name"] == "Pick up")["status"],
                         "unavailable")
        self.assertIn("already resolving", next(row for row in pending_catalog
                                                 if row["name"] == "Pick up")["reason"])
        status, settled = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(settled["pickup_action"]["outcome"], "success")
        self.assertEqual(native.parent_container_id, player.id)
        inventory = settled["character"]["inventory"]
        self.assertEqual(inventory["status"], "available")
        self.assertEqual(len(inventory["items"]), 1)
        self.assertEqual(inventory["items"][0]["name"], "My Dagger")
        self.assertEqual(inventory["items"][0]["status"], "carried; not readied")
        self.assertEqual(inventory["items"][0]["kind"], "weapon")
        self.assertEqual(inventory["items"][0]["weight_pounds"], native.current.weight)
        self.assertEqual(inventory["carried_weight_pounds"], native.current.weight)
        self.assertNotIn(native.id, json.dumps(inventory))
        self.assertIsNone(player.current.armor_id)
        ready_entry = next(row for row in settled["action_catalog"]["entries"]
                           if row["name"] == "ready weapon")
        self.assertEqual(ready_entry["status"], "unavailable")
        self.assertEqual(ready_entry["hands"], [])
        self.assertIn("no authored drawable source location", ready_entry["reason"])
        self.assertIn("Ground Pick up does not designate a sheath", ready_entry["reason"])
        self.assertEqual(ready_entry["target"]["handle"], target["handle"])
        time_before_ready_attempt = self.session.active_candidate.encounter.time
        status, refused_ready = self.request("/api/generated/ready-weapon",
            {"handle": target["handle"], "hand": "right hand"})
        self.assertEqual(status, 409)
        self.assertIn("drawable source location", refused_ready["error"])
        self.assertEqual(self.session.active_candidate.encounter.time, time_before_ready_attempt)
        inventory = self.session.public_view()["character"]["inventory"]
        self.assertEqual(len(inventory["items"]), 1)
        self.assertEqual(inventory["items"][0]["status"], "carried; not readied")
        self.assertEqual(inventory["carried_weight_pounds"], native.current.weight)
        self.assertEqual(player.current.body_parts, player.original.body_parts)
        hand_state = settled["character"]["anatomy"]
        self.assertEqual(hand_state["status"], "available")
        self.assertEqual({row["name"] for row in hand_state["hands"]},
                         set(player.current.body_parts) & {"left hand", "right hand"})
        self.assertTrue(all(row["occupancy"] == "empty" for row in hand_state["hands"]))
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [native.id])
        carried = next(row for row in self.session.public_view()["entities"]
                       if row["handle"] == target["handle"])
        self.assertEqual(carried["present_state"], "carried")
        self.assertIsNone(carried["position_meters"])
        self.assertNotIn(native.id, json.dumps(settled))
        self.assertEqual(carried["name"], "My Dagger")
        settled_pickup = next(row for row in settled["action_catalog"]["entries"]
                              if row["name"] == "Pick up")
        self.assertEqual(settled_pickup["status"], "unavailable")
        self.assertIn("free ground Object", settled_pickup["reason"])
        status, renamed_carried = self.request("/api/generated/rename-entity",
            {"handle": target["handle"], "name": "Carried Dagger"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed_carried["selected_entity"]["present_state"], "carried")
        self.assertEqual(renamed_carried["selected_entity"]["name"], "Carried Dagger")
        self.assertEqual(renamed_carried["character"]["inventory"]["items"][0]["name"],
                         "Carried Dagger")
        self.assertEqual(native.name, "Dagger")
        self.assertIsNone(native.spatial_state)
        self.assertEqual(native.parent_container_id, self.session.active_candidate.participants[0].native.being.id)
        next_cell = next(cell for cell in candidate.arena_map.layout.neighbors(
            HexAddress(target["cell"]["column"], target["cell"]["row"]))
                         if candidate.arena_map.layout.contains(cell))
        status, moving = self.request("/api/generated/destination", {
            "column": next_cell.column, "row": next_cell.row,
            "rate": "sprint", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        status, moving = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(moving["character"]["movement"]["position_meters"],
                         moving["player"]["position_meters"])
        self.assertEqual(len(moving["character"]["inventory"]["items"]), 1)
        self.assertEqual(moving["character"]["inventory"]["items"][0]["name"], "Carried Dagger")
        valid_weight = native.current.weight
        object.__setattr__(native.current, "weight", math.nan)
        invalid_inventory = self.session.public_view()["character"]["inventory"]
        self.assertEqual(invalid_inventory["status"], "unavailable")
        self.assertEqual(invalid_inventory["items"], [])
        self.assertIsNone(invalid_inventory["carried_weight_pounds"])
        native.current.weight = valid_weight
        trace = trace_stream.getvalue()
        self.assertIn("action=inspect status=accepted", trace)
        self.assertIn("action=pickup status=accepted", trace)
        self.assertIn("reason=arena_request_refused", trace)
        self.assertIn("action=rename_entity status=accepted", trace)
        self.assertIn("entity_type=object type=Dagger", trace)
        self.assertNotIn(native.id, trace)
        self.assertNotIn("http-dagger", trace)
        self.assertNotIn("My Dagger", trace)
        self.assertNotIn("Carried Dagger", trace)

    def test_authored_native_draw_http_choice_and_two_one_second_boundaries(self):
        from arena_perception import ArenaPerceptionEvidence
        from weapon import WeaponInstance, author_worn_sheath_draw_location

        _, page = self.request("/")
        self.assertIn("button.textContent=action.display_name||action.name", page)
        state = self.session.generate({
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        weapon_id = candidate.encounter.make_weapon("Dagger", "Test Drawer")
        weapon = candidate.universe.get_object_by_id(weapon_id)
        self.assertIs(type(weapon), WeaponInstance)
        player.possessions.append(weapon.id)
        weapon.parent_container_id = player.id
        player.current.body_parts["right hand"] = None
        author_worn_sheath_draw_location(weapon, player.id)
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
            "Dagger", None, "carried", 0, 0.0)
        ledger._current[weapon.id] = evidence
        ledger._history.append(evidence)

        status, activated = self.request("/api/generated/run", {})
        self.assertEqual(status, 200)
        status, activated = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        handle = next(row["handle"] for row in activated["entities"]
                      if row["type"] == "Dagger" and row["name"] == "Test Drawer")
        status, inspected = self.request("/api/generated/inspect", {"handle": handle})
        self.assertEqual(status, 200)
        draw = next(row for row in inspected["action_catalog"]["entries"]
                    if row["name"] == "ready weapon")
        self.assertEqual((draw["status"], draw["display_name"], draw["hands"]),
                         ("available", "Draw (2 s)", ["left hand", "right hand"]))
        status, accepted = self.request("/api/generated/ready-weapon",
            {"handle": handle, "hand": "right hand"})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["ready_weapon_action"]["seconds_remaining"], 2)
        self.assertEqual(accepted["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        status, first = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(first["ready_weapon_action"]["status"], "executing")
        self.assertEqual(first["ready_weapon_action"]["seconds_remaining"], 1)
        self.assertEqual(first["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertEqual(player.current.body_parts["right hand"], None)
        status, second = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(second["ready_weapon_action"]["status"], "completed")
        self.assertEqual(second["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(second["character"]["inventory"]["items"][0]["status"],
                         "readied in right hand")
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertEqual(player.weapons, [weapon.id])
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertNotIn(weapon.id, json.dumps(second))

    def test_generated_ready_delay_http_controls_and_visible_motion_timing(self):
        from weapon import native_ready_preparation
        scenario = json.loads((ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
                              .read_text(encoding="utf-8"))
        self.session = GeneratedArenaSession(authored_draw_scenario=scenario,
            root_seed_factory=lambda: 20261130)
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        weapon = next(obj for obj in self.session.active_candidate.universe.object_registry.object_instances.values()
                      if getattr(obj, "name", None) == "Drawable Dagger")
        handle = next(row["handle"] for row in state["entities"] if row["name"] == weapon.name)
        status, draw = self.request("/api/generated/ready-weapon",
            {"handle": handle, "hand": "right hand"})
        self.assertEqual(status, 200)
        self.request("/api/generated/advance", {"seconds": 1})
        status, drawn = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        status, inspected = self.request("/api/generated/inspect", {"handle": handle})
        self.assertEqual(status, 200)
        ready_row = next(row for row in inspected["action_catalog"]["entries"]
                         if row["name"] == "ready object")
        self.assertEqual(ready_row["motions"], [
            {"motion": "swing", "duration_seconds": 1},
            {"motion": "thrust", "duration_seconds": 1}])
        status, ready = self.request("/api/generated/ready-preparation",
            {"handle": handle, "motion": "swing"})
        self.assertEqual((status, ready["ready_preparation_action"]["duration_seconds"]),
                         (200, 1))
        status, committed = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual((status, committed["ready_preparation_action"]["outcome"]),
                         (200, "success"))
        self.assertEqual(native_ready_preparation(weapon)["motion"], "swing")
        status, waiting = self.request("/api/generated/delay", {"defense": 0})
        self.assertEqual((status, waiting["delay_action"]["status"]), (200, "executing"))
        status, waited = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual((status, waited["delay_action"]["outcome"]), (200, "success"))
        self.assertEqual(native_ready_preparation(weapon)["motion"], "swing")
        _, page = self.request("/")
        self.assertIn("/api/generated/ready-preparation", page)
        self.assertIn("/api/generated/delay", page)

    def test_pause_resume_http_controls_keep_action_identity_and_remaining_time(self):
        from activities import SpotAction
        status,_=self.request("/api/generated/generate",{
            "starting_experience":"1000","width_cells":"5","height_cells":"5",
            "equipment_mode":"unequipped","opponent_strategy":"none"})
        self.assertEqual(status,200)
        self.session.choose_run();self.session.advance_one_second()
        candidate=self.session.active_candidate;player,target=(r.native.being for r in candidate.participants)
        spot=SpotAction(candidate.universe,player.id,target.id,candidate.encounter.time)
        candidate.encounter.schedule_action(spot);candidate.encounter.step(2)
        status,paused=self.request('/api/generated/pause',{})
        self.assertEqual((status,paused['paused_action']['name'],paused['paused_action']['seconds_remaining']),
                         (200,'Spot',4))
        candidate.encounter.step(2)
        status,resumed=self.request('/api/generated/resume',{})
        self.assertEqual((status,resumed['paused_action'],candidate.encounter._choice_book.effective_end(spot)),
                         (200,None,9))
        _,page=self.request('/')
        self.assertIn('/api/generated/pause',page)
        self.assertIn('/api/generated/resume',page)

    def test_opt_in_scenario_selection_and_exact_fresh_process_continuation(self):
        scenario = json.loads((ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
                              .read_text(encoding="utf-8"))
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261126,
                                             authored_draw_scenario=scenario)
        self.assertTrue(self.session.public_view()["playable_scenario_available"])
        _, page = self.request("/")
        self.assertIn("Playable scenario", page)
        self.assertIn("Ordinary Dagger Draw · authored carried Dagger", page)
        self.assertIn("authored_scenario:$('playableScenario').value||null", page)
        status, ordinary = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "authored_scenario": None, "root_seed": "20261126"})
        self.assertEqual(status, 200)
        self.assertIsNone(ordinary["authored_scenario_id"])
        self.assertFalse(any(item["name"] == "Drawable Dagger"
                             for item in ordinary["character"]["inventory"]["items"]))
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "authored_scenario": "ordinary-dagger-draw", "root_seed": "20261126"})
        self.assertEqual(status, 200)
        self.assertEqual(state["authored_scenario_id"], "ordinary-dagger-draw")
        self.assertEqual(state["player"]["position_meters"]["z"], 0)
        weapon = next(item for item in state["character"]["inventory"]["items"]
                      if item["name"] == "Drawable Dagger")
        self.assertEqual(weapon["status"], "carried; not readied")
        status, pending = self.request("/api/generated/ready-weapon", {
            "handle": weapon["handle"], "hand": "right hand"})
        self.assertEqual((status, pending["ready_weapon_action"]["status"]), (200, "executing"))
        with tempfile.TemporaryDirectory(prefix="arena-scenario-fresh-process-") as temp:
            pending_path = Path(temp) / "pending.json"
            completed_path = Path(temp) / "completed.json"
            pending_path.write_bytes(self.session.save_encounter_bytes())
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                       PYTHONPATH=f"{ROOT / 'src'}:{ROOT / 'examples'}:{ROOT / 'tests'}")
            pending_code = """import json,sys; from pathlib import Path; from arena_browser_session import GeneratedArenaSession; s=GeneratedArenaSession(); v=s.load_encounter_bytes(Path(sys.argv[1]).read_bytes()); assert s._authored_scenario_id=='ordinary-dagger-draw'; assert v['ready_weapon_action']['status']=='executing'; assert v['ready_weapon_action']['seconds_remaining']==2; s.advance_one_second(); s.advance_one_second(); v=s.public_view(); assert v['ready_weapon_action']['status']=='completed'; assert v['authored_scenario_id']=='ordinary-dagger-draw'; Path(sys.argv[2]).write_bytes(s.save_encounter_bytes()); print(json.dumps({'scenario':v['authored_scenario_id'],'time':v['time_seconds'],'draw':v['ready_weapon_action']['status'],'held':v['character']['anatomy']['hands'][1]['occupancy']}))"""
            first = subprocess.run([sys.executable, "-B", "-c", pending_code,
                                    str(pending_path), str(completed_path)],
                                   cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout), {
                "scenario": "ordinary-dagger-draw", "time": 2, "draw": "completed", "held": "occupied"})
            restore_code = """import json,sys; from pathlib import Path; from arena_browser_session import GeneratedArenaSession; s=GeneratedArenaSession(); v=s.load_encounter_bytes(Path(sys.argv[1]).read_bytes()); assert s._authored_scenario_id=='ordinary-dagger-draw'; assert v['ready_weapon_action']['outcome']=='success'; assert v['character']['inventory']['items'][0]['status']=='readied in right hand'; print(json.dumps({'scenario':v['authored_scenario_id'],'time':v['time_seconds'],'draw':v['ready_weapon_action']['outcome'],'item':v['character']['inventory']['items'][0]['status']}))"""
            second = subprocess.run([sys.executable, "-B", "-c", restore_code,
                                     str(completed_path)], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout), {
                "scenario": "ordinary-dagger-draw", "time": 2, "draw": "success",
                "item": "readied in right hand"})

    def test_opt_in_draw_scenario_http_first_choice_and_forged_stale_refusal(self):
        from arena_authored_draw_scenario import validate_scenario

        scenario = validate_scenario(json.loads(
            (ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
            .read_text(encoding="utf-8")))
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261125,
                                             authored_draw_scenario=scenario)
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("button.textContent=action.display_name||action.name", page)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        opponent = candidate.participants[1].native.being
        weapon = candidate.universe.get_object_by_id(player.possessions[0])
        original_awareness = {key: set(value) for key, value in candidate.encounter.awareness.items()}
        time_before = candidate.encounter.time
        choices_before = dict(candidate.encounter._choice_book._choices)
        status, refused = self.request("/api/generated/ready-weapon",
                                       {"handle": "forged-handle", "hand": "right hand"})
        self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(candidate.encounter._choice_book._choices, choices_before)
        self.assertFalse(candidate.encounter.initiated)
        self.assertIn("carried Weapon", refused["error"])

        row = next(item for item in generated["entities"] if item["name"] == "Drawable Dagger")
        status, inspected = self.request("/api/generated/inspect", {"handle": row["handle"]})
        self.assertEqual(status, 200)
        action = next(item for item in inspected["action_catalog"]["entries"]
                      if item["name"] == "ready weapon")
        self.assertEqual((action["status"], action["display_name"], action["hands"]),
                         ("available", "Draw (2 s)", ["left hand", "right hand"]))
        self.assertEqual(inspected["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        weight = weapon.current.weight
        status, accepted = self.request("/api/generated/ready-weapon",
                                        {"handle": row["handle"], "hand": "right hand"})
        self.assertEqual(status, 200)
        self.assertEqual(candidate.encounter.arena_activation.activation_kind,
                         "first_player_choice")
        self.assertIsNone(candidate.encounter.initiation)
        self.assertEqual(candidate.encounter.awareness, original_awareness)
        self.assertEqual(accepted["ready_weapon_action"]["seconds_remaining"], 2)
        status, one = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual((one["time_seconds"], one["ready_weapon_action"]["status"],
                          one["ready_weapon_action"]["seconds_remaining"]), (1, "executing", 1))
        self.assertEqual(one["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertIsNone(player.current.body_parts["right hand"])
        status, two = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual((two["time_seconds"], two["ready_weapon_action"]["status"],
                          two["ready_weapon_action"]["outcome"]), (2, "completed", "success"))
        inventory = two["character"]["inventory"]
        self.assertEqual(inventory["items"][0]["status"], "readied in right hand")
        self.assertEqual(inventory["items"][0]["weight_pounds"], weight)
        self.assertEqual(inventory["carried_weight_pounds"], weight)
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(player.weapons, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertNotIn(opponent.id, json.dumps(two["character"]))
        self.assertNotIn(weapon.id, json.dumps(two))
        stale_handle = row["handle"]

        status, invalid_generate = self.request("/api/generated/generate", {
            "starting_experience": "not-an-integer", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 409)
        self.assertIs(self.session.active_candidate, candidate)
        self.assertEqual(self.session.public_view(), two)
        self.session.generate({"starting_experience": "10000", "width_cells": "10",
                               "height_cells": "5"})
        status, stale = self.request("/api/generated/ready-weapon",
                                     {"handle": stale_handle, "hand": "right hand"})
        self.assertEqual(status, 409)
        self.assertIn("carried Weapon", stale["error"])

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("swift"),
                         "JavaScriptCore via Swift is available on macOS only")
    def test_actual_shipped_javascript_runs_fresh_authored_draw_scenario(self):
        import tempfile

        scenario = json.loads((ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
                              .read_text(encoding="utf-8"))
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261126,
                                             authored_draw_scenario=scenario)
        state = self.session.generate({
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        _, page = self.request("/")
        with tempfile.TemporaryDirectory(prefix="arena-authored-draw-js-") as temp:
            page_path = Path(temp) / "page.html"
            state_path = Path(temp) / "initial-state.json"
            cell_path = Path(temp) / "target-cell.json"
            pickup_path = Path(temp) / "pickup-view.json"
            page_path.write_text(page, encoding="utf-8")
            state_path.write_text(json.dumps(state), encoding="utf-8")
            cell_path.write_text(json.dumps({"column": 0, "row": 0}), encoding="utf-8")
            pickup_path.write_text(json.dumps(state), encoding="utf-8")
            module_cache = Path(tempfile.gettempdir()) / "universe-arena-jsc-module-cache"
            module_cache.mkdir(parents=True, exist_ok=True)
            harness = ROOT / "tests" / "arena_browser_js_harness.swift"
            run = subprocess.run([shutil.which("swift"), "-module-cache-path", str(module_cache),
                str(harness), str(page_path), str(state_path), str(cell_path), str(pickup_path),
                "null", "draw-only"], check=False, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["time"], 2)
        self.assertEqual(result["activationRunCalls"], 0)
        self.assertEqual(result["inventory"][0]["status"], "readied in right hand")
        self.assertEqual(result["drawCall"]["body"]["hand"], "right hand")
        self.assertIn("left hand: empty", result["characterText"])
        self.assertIn("right hand: Drawable Dagger — Dagger", result["characterText"])
        self.assertNotIn("native_id", json.dumps(result["drawCall"]["body"]))
        self.assertEqual([call["path"] for call in result["calls"] if call["path"] in (
            "/api/generated/ready-weapon", "/api/generated/advance")], [
            "/api/generated/ready-weapon", "/api/generated/advance", "/api/generated/advance"])

    def test_display_name_overlay_is_safe_observer_scoped_and_replacement_atomic(self):
        original_history = None
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        initial = self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        candidate_identity = candidate
        self.assertEqual(candidate.ground_objects, ())
        self.assertEqual(initial["character"]["inventory"]["status"], "available")
        self.assertEqual(initial["character"]["inventory"]["items"], [])
        self.assertEqual(initial["character"]["inventory"]["carried_weight_pounds"], 0.0)
        player, opponent = (row.native.being for row in candidate.participants)
        opponent_view = next(row for row in initial["entities"] if row["category"] == "being")
        native_name, native_id = opponent.name, opponent.id
        ledger = player._arena_perception_ledger
        original_history = tuple(ledger.history)
        original_current = dict(ledger._current)
        awareness = candidate.encounter.aware_beings(player.id)
        choices = dict(candidate.encounter._choice_book._choices)
        time_before = candidate.encounter.time
        rng_before = self.session._rng_cursor.state
        status, renamed = self.request("/api/generated/rename-entity", {
            "handle": opponent_view["handle"], "name": "Mira <b>"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed["selected_entity"]["name"], "Mira <b>")
        self.assertEqual(opponent.id, native_id)
        self.assertEqual(opponent.name, native_name)
        self.assertEqual(tuple(ledger.history), original_history)
        self.assertEqual(ledger._current, original_current)
        self.assertEqual(candidate.encounter.aware_beings(player.id), awareness)
        self.assertEqual(candidate.encounter._choice_book._choices, choices)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        self.assertNotIn(native_id, json.dumps(renamed))
        self.assertNotIn("source_record", json.dumps(renamed))
        before_refusal = self.session.public_view()
        for invalid_name in ("", " " * 2, "x" * 41):
            status, _ = self.request("/api/generated/rename-entity", {
                "handle": opponent_view["handle"], "name": invalid_name})
            self.assertEqual(status, 409)
            self.assertEqual(self.session.public_view(), before_refusal)
        status, _ = self.request("/api/generated/rename-entity", {
            "handle": "forged-handle", "name": "Nope"})
        self.assertEqual(status, 409)
        status, _ = self.request("/api/generated/rename-entity", {
            "handle": opponent_view["handle"], "name": "Nope", "extra": 1})
        self.assertEqual(status, 409)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "not-an-integer", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 409)
        self.assertEqual(next(row for row in self.session.public_view()["entities"]
                              if row["handle"] == opponent_view["handle"])["name"], "Mira <b>")
        self.assertIs(self.session.active_candidate, candidate_identity)
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        fresh = self.session.public_view()
        self.assertTrue(all(row["name"] != "Mira <b>" for row in fresh["entities"]))
        status, _ = self.request("/api/generated/rename-entity", {
            "handle": opponent_view["handle"], "name": "Stale"})
        self.assertEqual(status, 409)
        self.assertEqual(self.session.active_candidate.encounter.time, 0)

    def test_character_sheet_reads_native_state_without_history_or_opponent_disclosure(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        initial = self.session.generate({"starting_experience": "10000",
                                         "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        player, opponent = (row.native.being for row in candidate.participants)
        rng_before, time_before = self.session._rng_cursor.state, candidate.encounter.time
        event_history_before = dict(candidate.universe.event_history)
        player_ledger = player._arena_perception_ledger
        history_before = tuple(player_ledger.history)
        character_a = self.session.public_view()["character"]
        character_b = self.session.public_view()["character"]
        self.assertEqual(character_a, character_b)
        self.assertEqual(character_a["experience"]["total"], player.get_experience())
        self.assertEqual({row["name"]: row["score"] for row in character_a["abilities"]},
                         player.current.get_abilities())
        self.assertEqual(character_a["condition"]["physical_fatigue_reserves"], {
            "q": player.physical_fatigue.q, "b": player.physical_fatigue.b,
            "profile_status": "unresolved"})
        opponent_view = next(row for row in initial["entities"]
                             if row["category"] == "being" and row["handle"] != initial["player"].get("handle"))
        inspected = self.session.inspect_entity({"handle": opponent_view["handle"]})
        self.assertEqual(inspected["selected_entity"]["category"], "being")
        for private_key in ("abilities", "skills", "experience", "condition", "possessions", "source_record"):
            self.assertNotIn(private_key, inspected["selected_entity"])
        self.assertEqual(inspected["character"]["identity"]["display_name"], initial["player"]["name"])
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        self.assertEqual(candidate.universe.event_history, event_history_before)
        self.assertEqual(tuple(player_ledger.history), history_before)

        player.possessions.append("missing-native-object-reference")
        unavailable = self.session.public_view()["character"]["inventory"]
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["items"], [])
        self.assertIn("validation failed", unavailable["encumbrance_status"])
        self.assertNotIn("missing-native-object-reference", json.dumps(unavailable))
        player.possessions.clear()

    def test_strict_server_inputs_and_failed_regeneration_leave_active_session_unchanged(self):
        for payload in (
            {"starting_experience": 0, "width_cells": "5", "height_cells": "5"},
            {"starting_experience": "0.0", "width_cells": "5", "height_cells": "5"},
            {"starting_experience": "0", "width_cells": "4", "height_cells": "5"},
            {"starting_experience": "0", "width_cells": "1001", "height_cells": "1000"},
        ):
            status, body = self.request("/api/generated/generate", payload)
            self.assertEqual(status, 409)
            self.assertIn("error", body)
        status, original = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 200)
        self.request("/api/generated/player-name", {"name": "Keep me"})
        active = self.session.active_candidate
        previous = self.session.public_view()
        status, body = self.request("/api/generated/generate", {
            "starting_experience": str(2**53), "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 409)
        self.assertIn("npcgen", body["error"].lower())
        self.assertIs(self.session.active_candidate, active)
        self.assertEqual(self.session.public_view(), previous)
        self.assertEqual(active.encounter.time, original["time_seconds"])
        self.assertEqual(self.request("/api/load", {})[0], 404)

    def test_name_refusals_and_unavailable_routes_do_not_change_active_world(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        before = self.session.public_view()
        for path, body in (("/api/generated/player-name", {"name": "  "}),
                            ("/api/generated/player-name", {"name": "x" * 41}),
                            ("/api/generated/encounter-name", {"name": "ok", "extra": 1}),
                            ("/api/generated/spot", {"operation": "spot"}),
                            ("/api/generated/advance", {"seconds": 1}),
                            ("/api/spot", {"operation": "ari_spots_bex"}),
                            ("/api/advance", {"seconds": 1})):
            status, _ = self.request(path, body)
            self.assertNotEqual(status, 200)
            self.assertEqual(self.session.public_view(), before)

    def test_native_invalid_first_choice_leaves_unstarted_arena_unchanged(self):
        from activities import RunAction
        from action_choice import ChoiceRejected

        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        # The declaration is otherwise a valid Run Choice but collides with the
        # already-registered Encounter Event identity during native preflight.
        action = RunAction(candidate.universe, player.id, 0, 1, 0.1,
                          experience=0, id=encounter.id)
        before_history = dict(candidate.universe.event_history)
        before_view = self.session.public_view()
        before_revision = encounter._choice_book.revision
        before_counter = encounter._choice_book._counter
        rng_state = self.session._rng_cursor.state
        with self.assertRaises(ChoiceRejected):
            encounter.activate_arena_for_player_action(
                player.id, action, rng_owner=self.session._rng_cursor)
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_activation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter.pending_action_list, [])
        self.assertEqual(encounter._choice_book._choices, {})
        self.assertEqual(encounter._choice_book._counter, before_counter)
        self.assertEqual(encounter._choice_book._drafts, {})
        self.assertEqual(encounter._choice_book._tokens, {})
        self.assertEqual(encounter._choice_book.revision, before_revision)
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        self.assertEqual(self.session.public_view(), before_view)

    def test_activation_rolls_back_if_native_mode_selection_aborts_after_publication(self):
        from activities import RunAction
        from unittest.mock import patch

        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        action = RunAction(candidate.universe, player.id, 0, 1, 0.1, experience=0)
        before_history = dict(candidate.universe.event_history)
        before_view = self.session.public_view()
        before_revision = encounter._choice_book.revision
        before_counter = encounter._choice_book._counter
        rng_state = self.session._rng_cursor.state
        with patch("transactional_progression._enable_transactional_progression_owned",
                   side_effect=RuntimeError("injected pre-commit abort")):
            with self.assertRaises(RuntimeError):
                encounter.activate_arena_for_player_action(
                    player.id, action, rng_owner=self.session._rng_cursor)
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_activation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter.pending_action_list, [])
        self.assertEqual(encounter._choice_book._choices, {})
        self.assertEqual(encounter._choice_book._registered, {})
        self.assertEqual(encounter._choice_book._counter, before_counter)
        self.assertEqual(encounter._choice_book._drafts, {})
        self.assertEqual(encounter._choice_book._tokens, {})
        self.assertEqual(encounter._choice_book.revision, before_revision)
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        self.assertEqual(self.session.public_view(), before_view)

    def test_movement_activation_rolls_back_without_choice_or_rng_changes(self):
        from unittest.mock import patch

        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        before_view = self.session.public_view()
        before_history = dict(candidate.universe.event_history)
        before_choices = dict(encounter._choice_book._choices)
        before_revision = encounter._choice_book.revision
        rng_state = self.session._rng_cursor.state
        with patch("transactional_progression._enable_transactional_progression_owned",
                   side_effect=RuntimeError("injected pre-commit abort")):
            with self.assertRaises(ArenaBrowserRequestError):
                self.session.choose_destination({"column": 4, "row": 4,
                    "rate": "walk", "facing_policy": "turn"})
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_movement_activation)
        self.assertIsNone(encounter.arena_activation)
        self.assertIsNone(encounter.initiation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter._choice_book._choices, before_choices)
        self.assertEqual(encounter._choice_book.revision, before_revision)
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        self.assertEqual(self.session.public_view(), before_view)

    def test_generated_run_choice_activates_then_commits_one_native_second(self):
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        start = player.native.being.get_position()

        status, accepted = self.request("/api/generated/run", {})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["time_seconds"], 0)
        self.assertTrue(accepted["advance_available"])
        self.assertEqual(encounter.progression_mode, "transactional")
        self.assertTrue(encounter.initiated)
        activation = encounter.arena_activation
        self.assertEqual(activation.actor_id, player.native.being.id)
        self.assertEqual(activation.time, 0)
        self.assertEqual(activation.activation_kind, "first_player_choice")
        self.assertFalse(hasattr(activation, "target_id"))
        self.assertIsNone(encounter.initiation)
        self.assertEqual(encounter.aware_beings(player.native.being.id), [hidden.native.being.id])
        encoded = json.dumps(accepted).lower()
        for forbidden in (hidden.native.being.id.lower(), "target_id", "activation", "source_record"):
            self.assertNotIn(forbidden, encoded)

        status, advanced = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(advanced["time_seconds"], 1)
        self.assertEqual(advanced["player"]["cell"], accepted["player"]["cell"])
        self.assertEqual(advanced["player_action"],
                         {"name": "Run", "status": "completed", "outcome": "no_movement"})
        self.assertEqual(advanced["player"]["position_meters"],
                         {"x": start.x, "y": start.y, "z": start.z})
        action_id = encounter._choice_book._choices[activation.choice_id].view.action_ids[0]
        native_result = encounter.inspect_committed(1).action(action_id)
        self.assertEqual(native_result.facts.outcome, "no_movement")
        self.assertEqual(encounter.time, 1)
        self.assertEqual(encounter.aware_beings(player.native.being.id), [hidden.native.being.id])
        self.assertNotIn(hidden.native.being.id, json.dumps(advanced))
        before = self.session.public_view()
        self.assertNotEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(self.session.public_view(), before)

    def test_destination_movement_activates_without_action_and_arrives_from_native_commits(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        being = player.native.being
        start = being.get_position()
        layout = candidate.arena_map.layout
        addresses = [HexAddress(column, row)
                     for column in range(candidate.arena_map.width_cells)
                     for row in range(candidate.arena_map.height_cells)]
        target_address = max(addresses, key=lambda address: math.dist(
            start.as_tuple(), layout.center_position(address, z=start.z).as_tuple()))
        target = layout.center_position(target_address, z=start.z)
        self.assertGreater(math.dist(start.as_tuple(), target.as_tuple()), 0)
        expected_facing = nearest_facing((target.x - start.x, target.y - start.y,
                                           target.z - start.z))
        before_history = dict(candidate.universe.event_history)
        before_choices = dict(encounter._choice_book._choices)
        before_awareness = (encounter.aware_beings(being.id),
                            encounter.aware_beings(hidden.native.being.id))
        before_rng = self.session._rng_cursor.state
        before_global_rng = random.getstate()

        status, selected = self.request("/api/generated/destination", {
            "column": target_address.column, "row": target_address.row,
            "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        self.assertEqual(encounter.time, 0)
        self.assertTrue(encounter.initiated)
        self.assertEqual(encounter.progression_mode, "transactional")
        activation = encounter.arena_movement_activation
        self.assertEqual(activation.actor_id, being.id)
        self.assertEqual(activation.movement_decision_id, "arena-movement-1")
        self.assertEqual(activation.time, 0)
        self.assertIsNone(encounter.arena_activation)
        self.assertIsNone(encounter.initiation)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter._choice_book._choices, before_choices)
        self.assertEqual(before_awareness, (encounter.aware_beings(being.id),
                                           encounter.aware_beings(hidden.native.being.id)))
        self.assertTrue(selected["advance_available"])
        self.assertEqual(selected["movement_plan"]["rate"], "walk")
        self.assertNotIn(hidden.native.being.id, json.dumps(selected))

        committed = []
        while self.session.public_view()["movement_plan"] is not None:
            before = being.get_position()
            status, view = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            after = being.get_position()
            committed.append(after)
            self.assertEqual(view["player"]["position_meters"],
                             {"x": after.x, "y": after.y, "z": after.z})
            self.assertGreater((after.x - before.x) ** 2 + (after.y - before.y) ** 2, 0)
            self.assertEqual(view["time_seconds"], encounter.time)
            self.assertNotIn(hidden.native.being.id, json.dumps(view))
            perceived_opponent = next(row for row in view["entities"]
                                      if row["category"] == "being")
            opponent_position = hidden.native.being.get_position()
            self.assertEqual(perceived_opponent["position_meters"], {
                "x": opponent_position.x, "y": opponent_position.y, "z": opponent_position.z})
            if len(committed) == 1:
                self.assertEqual(being.hex_facing, expected_facing)
        final = self.session.public_view()
        self.assertGreater(len(committed), 1)
        self.assertEqual(being.get_position(), truncate_position(target))
        committed_target = truncate_position(target)
        self.assertEqual(final["player"]["position_meters"],
                         {"x": committed_target.x, "y": committed_target.y,
                          "z": committed_target.z})
        self.assertEqual(final["player"]["cell"], {
            "column": target_address.column, "row": target_address.row})
        self.assertEqual(final["movement_outcome"], "arrived")
        self.assertIsNone(final["movement_plan"])
        self.assertEqual(encounter.aware_beings(being.id), [hidden.native.being.id])
        self.assertEqual(encounter.aware_beings(hidden.native.being.id), [being.id])
        self.assertEqual(encounter._choice_book._choices, {})
        self.assertEqual(self.session._rng_cursor.state, before_rng)
        self.assertEqual(random.getstate(), before_global_rng)

    def test_destination_can_be_changed_or_stopped_at_a_committed_boundary(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        being = candidate.participants[0].native.being
        start = candidate.arena_map.layout.center_position(HexAddress(0, 0))
        being.set_position(start)
        being.set_hex_facing(0)
        self.request("/api/generated/destination", {
            "column": 4, "row": 4, "rate": "walk", "facing_policy": "maintain"})
        self.request("/api/generated/advance", {"seconds": 1})
        committed = being.get_position()
        status, changed = self.request("/api/generated/destination", {
            "column": 0, "row": 4, "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        self.assertEqual(being.get_position(), committed)
        self.assertEqual(changed["movement_plan"]["destination_cell"], {"column": 0, "row": 4})
        self.assertEqual(changed["movement_plan"]["facing_policy"], "turn")
        self.assertEqual(changed["time_seconds"], 1)
        status, stopped = self.request("/api/generated/stop", {})
        self.assertEqual(status, 200)
        self.assertEqual(being.get_position(), committed)
        self.assertIsNone(stopped["movement_plan"])
        self.assertEqual(stopped["movement_outcome"], "stopped")
        before = self.session.public_view()
        self.assertNotEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(self.session.public_view(), before)

    def test_unknown_posture_rejects_destination_without_activation_or_publication(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        being = candidate.participants[0].native.being
        being.set_posture(None)
        before = self.session.public_view()
        with self.assertRaises(ArenaBrowserRequestError):
            self.session.choose_destination({"column": 4, "row": 4,
                                             "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(self.session.public_view(), before)
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_movement_activation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(encounter._choice_book._choices, {})

    def test_initial_passive_awareness_makes_spot_intent_unnecessary_without_geometry(self):
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        self.assertIsNone(player.native.being.geometry)
        self.assertIsNone(hidden.native.being.geometry)
        # This explicit flag isolates the geometry gate in this test. It is
        # not a generated-Arena activation path or an initiation proof.
        encounter.initiated = True
        cursor = RNGCursor(random.Random(17).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=cursor)
        intent = accept_spot_attention(encounter, player.native.being.id)
        self.assertFalse(intent.accepted)
        self.assertEqual(intent.status, "not_accepted")
        self.assertEqual(encounter.aware_beings(player.native.being.id), [hidden.native.being.id])

    def test_generated_stun_program_survives_fresh_load_and_interrupts_later_action(self):
        from dataclasses import replace
        from action_evaluation import RandomDraw, _ProvisionalRandom
        from melee_combat import MeleeStrike
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261119,
            ground_loadout_profile=json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text()))
        page = self.request("/")[1]
        self.assertIn('kind==="stun"&&a.motions?.length', page)
        self.assertIn('kind==="subdue"&&a.weapon_options?.length', page)
        self.assertEqual(self.request("/api/generated/generate", {
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})[0], 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        player.set_position(CartesianPosition(1.0, 1.0, 0))
        target.set_position(CartesianPosition(1.1, 1.0, 0))
        player.set_hex_facing(nearest_facing((target.get_position().x-player.get_position().x,
            target.get_position().y-player.get_position().y,0)))
        target.set_hex_facing(nearest_facing((player.get_position().x-target.get_position().x,
            player.get_position().y-target.get_position().y,0)))
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "unarmed combat", 5)
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "stun", 1)
        player.current.tags["universe.stun_categories"] = {"humanoid": 2}
        target.current.tags["universe.stun_category"] = "humanoid"
        weapon_id = candidate.universe.make_weapon_for_being(target.id, "Dagger", "Scenario Dagger")
        candidate.universe.arm_being(target.id, weapon_id, "right hand")
        target.set_weapon_skill_level(candidate.universe.get_skill_dictionary(), "Dagger", 3)
        encounter.mark_aware(player.id, target.id)
        encounter.mark_aware(target.id, player.id)
        evidence = replace(player._arena_perception_ledger._current[target.id],
                           position=target.get_position())
        player._arena_perception_ledger._current[target.id] = evidence
        player._arena_perception_ledger._history = [evidence if row.entity_id == target.id else row
            for row in player._arena_perception_ledger._history]
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        incoming = MeleeStrike(encounter, target.id, player.id, weapon_id,
                               motion="swing", reach=2)
        encounter.schedule_action(incoming)
        target_handle = self.session._view_handles[target.id]
        inspected = self.request("/api/generated/inspect", {"handle": target_handle})
        self.assertEqual(inspected[0], 200)
        stun_row = next(row for row in inspected[1]["action_catalog"]["entries"]
                        if row["name"] == "Stun")
        self.assertEqual(stun_row["status"], "available", stun_row["reason"])
        status, accepted = self.request("/api/generated/action-program", {"components": [{
            "kind": "stun", "handle": target_handle, "body_region": "Arm",
            "motion": "thrust"}]})
        self.assertEqual(status, 200, accepted)
        stun_action_id = next(member.action.id
            for record in encounter._choice_book._choices.values()
            for member in record.members if member.action.event_type == "stun")
        pending = self.session.save_encounter_bytes()
        restored = GeneratedArenaSession(root_seed_factory=lambda: 99)
        loaded = restored.load_encounter_bytes(pending)
        restored_encounter = restored.active_candidate.encounter
        stun_record = next(record for record in restored_encounter._choice_book._choices.values()
            if any(member.action.id == stun_action_id for member in record.members))
        self.assertEqual(stun_record.view.state, "accepted")
        self.assertTrue(any(component["name"] == "Stun"
                            for program in loaded["action_programs"]
                            for component in program["components"]))
        stun_action = next(member.action for member in stun_record.members
                           if member.action.id == stun_action_id)
        values = iter((19, 1, 1, 1))
        def roll(context, dice):
            value = next(values)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", roll):
            for _ in range(5):
                loaded = restored.advance_one_second()
                if incoming.id in restored.active_candidate.encounter.cancelled_action_list:
                    break
        restored_encounter = restored.active_candidate.encounter
        restored_world = restored.active_candidate.universe
        result_target = restored_world.get_object_by_id(target.id)
        self.assertEqual(stun_action.resolution.outcome, "stunned")
        self.assertIn(incoming.id, restored_encounter.cancelled_action_list)
        self.assertGreater(result_target.current.states.states["stunned_until"],
                           restored_encounter.time)
        committed = restored.save_encounter_bytes()
        second_process = GeneratedArenaSession(root_seed_factory=lambda: 100)
        second_process.load_encounter_bytes(committed)
        self.assertEqual(second_process.active_candidate.encounter.id, encounter.id)

    def test_generated_subdue_http_fresh_load_and_independent_condition(self):
        from dataclasses import replace
        from action_evaluation import RandomDraw, SubdualEffect, DamageEffect, _ProvisionalRandom
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261120,
            ground_loadout_profile=json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text()))
        self.assertEqual(self.request("/api/generated/generate", {
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "equipment_mode": "unequipped", "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})[0], 200)
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        player.set_position(CartesianPosition(1.0, 1.0, 0))
        target.set_position(CartesianPosition(1.1, 1.0, 0))
        player.set_hex_facing(nearest_facing((target.get_position().x-player.get_position().x,
            target.get_position().y-player.get_position().y,0)))
        target.set_hex_facing(nearest_facing((player.get_position().x-target.get_position().x,
            player.get_position().y-target.get_position().y,0)))
        target.current.hit_points = 1
        encounter.difficulty_class = 1
        player.set_weapon_skill_level(candidate.universe.get_skill_dictionary(), "Club", 3)
        club_id = candidate.universe.make_weapon_for_being(player.id, "Club", "Scenario Club")
        candidate.universe.arm_being(player.id, club_id, "right hand")
        encounter.mark_aware(player.id, target.id)
        encounter.mark_aware(target.id, player.id)
        evidence = replace(player._arena_perception_ledger._current[target.id],
                           position=target.get_position())
        player._arena_perception_ledger._current[target.id] = evidence
        player._arena_perception_ledger._history = [evidence if row.entity_id == target.id else row
            for row in player._arena_perception_ledger._history]
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.session.public_view()
        target_handle = self.session._view_handles[target.id]
        weapon_handle = self.session._view_handles[club_id]
        inspected = self.request("/api/generated/inspect", {"handle": target_handle})
        self.assertEqual(inspected[0], 200)
        subdue_row = next(row for row in inspected[1]["action_catalog"]["entries"]
                          if row["name"] == "Subdue")
        self.assertEqual(subdue_row["status"], "available", subdue_row["reason"])
        status, accepted = self.request("/api/generated/action-program", {"components": [{
            "kind": "subdue", "handle": target_handle, "weapon_handle": weapon_handle,
            "motion": "swing"}]})
        self.assertEqual(status, 200, accepted)
        action_id = next(member.action.id
            for record in encounter._choice_book._choices.values()
            for member in record.members if member.action.event_type == "subdue")
        pending = self.session.save_encounter_bytes()
        restored = GeneratedArenaSession(root_seed_factory=lambda: 101)
        restored.load_encounter_bytes(pending)
        restored_encounter = restored.active_candidate.encounter
        record = next(record for record in restored_encounter._choice_book._choices.values()
            if any(member.action.id == action_id for member in record.members))
        self.assertEqual(record.view.state, "accepted")
        subdue = next(member.action for member in record.members if member.action.id == action_id)
        values = iter((10, 1))
        def roll(context, dice):
            value = next(values) if dice == "1d20" or dice.startswith("1d") else 1
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", roll):
            for _ in range(8):
                view = restored.advance_one_second()
                if subdue.id in restored_encounter.finished_action_list:
                    break
        restored_world = restored.active_candidate.universe
        restored_target = restored_world.get_object_by_id(target.id)
        self.assertEqual(subdue.resolution.outcome, "normal")
        burden = next(effect.amount for effect in subdue.resolution.effects
                      if type(effect) is SubdualEffect)
        hp_damage = sum(effect.amount for effect in subdue.resolution.effects
            if type(effect) is DamageEffect and effect.component in ("body", "critical_bypass"))
        self.assertEqual(burden, 1)
        self.assertEqual(hp_damage, 0)
        self.assertEqual(restored_target.current.hit_points, 1)
        self.assertTrue(restored_target.current.states.states["subdual_unconscious"])
        restored_encounter.inspect_committed()
        saved_condition = restored.save_encounter_bytes()
        another = GeneratedArenaSession(root_seed_factory=lambda: 102)
        another.load_encounter_bytes(saved_condition)
        again = another.active_candidate.universe.get_object_by_id(target.id)
        self.assertEqual(again.current.hit_points, 1)
        self.assertEqual(again.current.states.states["subdual_damage"], 1)
        self.assertTrue(again.current.states.states["subdual_unconscious"])
        self.assertTrue(again.is_helpless())
        from action_evaluation import subdual_recovery_state
        recovery_anchor = again.current.states.states["subdual_recovery_anchor"]
        self.assertEqual(subdual_recovery_state(1, recovery_anchor,
                         recovery_anchor+3599), (1, recovery_anchor))
        self.assertEqual(subdual_recovery_state(1, recovery_anchor,
                         recovery_anchor+3600), (0, recovery_anchor+3600))

    def test_passive_refresh_refuses_later_unmodeled_geometry_without_partial_publication(self):
        from spatial.geometry import Sphere
        self.session.generate({"starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        other = candidate.participants[1].native.being
        initial_view = self.session.public_view()
        initial_ledger = (dict(player._arena_perception_ledger._current),
                          list(player._arena_perception_ledger._history))
        other.set_geometry(Sphere(.25))
        target = next(cell for cell in candidate.arena_map.layout.addresses()
                      if candidate.arena_map.layout.center_position(cell) != player.get_position())
        self.session.choose_destination({"column": target.column, "row": target.row,
                                         "rate": "walk", "facing_policy": "turn"})
        with self.assertRaisesRegex(ArenaBrowserRequestError, "state is unchanged"):
            self.session.advance_one_second()
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(player._arena_perception_ledger._current, initial_ledger[0])
        self.assertEqual(player._arena_perception_ledger._history, initial_ledger[1])
        self.assertEqual(self.session.public_view()["player"], initial_view["player"])


if __name__ == "__main__":
    unittest.main()
