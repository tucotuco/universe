"""Portable generated-Arena save/load integration tests."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena_browser_session import GeneratedArenaSession
from arena_browser_session import ArenaBrowserRequestError
from arena_hex_map import HexAddress
from activities import DelayAction, ThrowAction


class TestArenaPersistence(unittest.TestCase):
    @staticmethod
    def _tuplify(value):
        return tuple(TestArenaPersistence._tuplify(row) for row in value) if type(value) is list else value

    def _new_moving_session(self, *, ground_loadout_profile=None):
        seed = 20261026 if ground_loadout_profile is not None else 20261107
        session = GeneratedArenaSession(root_seed_factory=lambda: seed,
                                       ground_loadout_profile=ground_loadout_profile)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        position = candidate.participants[0].native.being.get_position()
        layout = candidate.arena_map.layout
        if ground_loadout_profile is None:
            address = max(layout.addresses(), key=lambda cell:
                math.dist(layout.center_position(cell, z=position.z).as_tuple(),
                          position.as_tuple()))
        else:
            origin = layout.cell_at_position(position)
            object_cells = {HexAddress(item.column, item.row)
                            for item in candidate.ground_objects}
            occupied_cells = {layout.cell_at_position(row.native.being.get_position())
                for row in candidate.participants[1:]}
            from movement_intent import MovementIntentRefusal, _movement_hexes
            clear_routes = []
            for cell in layout.addresses():
                if cell == origin or cell in occupied_cells:
                    continue
                destination = layout.center_position(cell, z=position.z)
                try:
                    route = _movement_hexes(position, destination, layout) - {origin}
                except MovementIntentRefusal:
                    continue
                if not route & object_cells and not route & occupied_cells:
                    clear_routes.append((math.dist(destination.as_tuple(), position.as_tuple()), cell))
            # Keep the route long enough to remain a pending movement choice
            # after the first saved boundary, while avoiding every represented
            # ground Object and other Being along its generated hex path.
            address = max(clear_routes, default=(None, None))[1]
            if address is None:
                raise AssertionError("ground-object fixture needs a representable clear path")
        session.choose_destination({"column": address.column, "row": address.row,
                                   "rate": "walk", "facing_policy": "turn"})
        return session

    def test_pristine_ground_objects_restore_with_native_identity_and_evidence(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        source = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                       ground_loadout_profile=profile)
        source.generate({"starting_experience": "10000",
                         "width_cells": "5", "height_cells": "5"})
        candidate = source.active_candidate
        object_ids = tuple(candidate.encounter.non_being_object_list)
        saved = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        view = restored.load_encounter_bytes(saved)
        loaded = restored.active_candidate
        self.assertEqual(tuple(loaded.encounter.non_being_object_list), object_ids)
        self.assertEqual(len(loaded.ground_objects), 8)
        self.assertEqual(len(view["entities"]), 9)
        for object_id in object_ids:
            before = candidate.universe.get_object_by_id(object_id)
            after = loaded.universe.get_object_by_id(object_id)
            self.assertIs(type(after), type(before))
            self.assertEqual(after.original.obj_type, before.original.obj_type)
            self.assertEqual(after.get_position(), before.get_position())
            self.assertEqual(after.parent_container_id, before.parent_container_id)
        for source_being, loaded_participant in zip(
                candidate.participants, loaded.participants):
            self.assertEqual(source_being.native.being._arena_perception_ledger.history,
                             loaded_participant.native.being._arena_perception_ledger.history)

    def test_generated_throw_pending_and_in_flight_survive_fresh_process(self):
        # NPC and measured stature come from npcgen. The Rock and placement
        # are explicit native scenario facts; no Browser request mutates the
        # generated world graph.
        source = GeneratedArenaSession(root_seed_factory=lambda: 5051)
        source.generate({"starting_experience": "10000",
                         "width_cells": "10", "height_cells": "5",
                         "opponent_strategy": "none"})
        candidate = source.active_candidate
        being = candidate.participants[0].native.being
        target = candidate.participants[1].native.being
        encounter = candidate.encounter
        universe = candidate.universe
        self.assertEqual(being.current.abilities.STR(), 10)
        object_id = universe.make_object_for_being(being.id, "Rock", "Scenario Rock")
        projectile = universe.get_object_by_id(object_id)
        projectile.set_position(being.get_position())
        encounter.add_object(object_id)
        encounter.activate_arena_for_player_action(being.id,
            DelayAction(encounter, being.id, 0, encounter.time),
            rng_owner=source._rng_cursor)
        encounter.step(1)
        throw = ThrowAction(universe, being.id, object_id, encounter.time,
            heavy_load_reference_lb=80, elevation_degrees=80,
            target_id=target.id,
            id="arena-test/throw")
        encounter.schedule_action(throw)
        encounter.step(1)
        self.assertIn(throw.id, encounter.pending_action_list)
        pending_bytes = source.save_encounter_bytes()

        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending-throw.json"
            airborne = Path(directory) / "airborne-throw.json"
            impact = Path(directory) / "impact-throw.json"
            pending.write_bytes(pending_bytes)
            script = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
from activities import ThrowAction
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter;o=c.universe.get_object_by_id(sys.argv[3])
assert any(type(c.universe.event_history[action_id]) is ThrowAction
           for action_id in e.pending_action_list)
e.step(3)
f=o.__dict__['_projectile_flight'];h=o.__dict__['_atomic_projectile_history']
assert f.status=='in_flight' and h[-1].boundary==5
pathlib.Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(json.dumps({'time':e.time,'id':o.id,'position':o.get_position().as_tuple(),
 'flight':(f.release_time,f.impact_time,f.release_position.as_tuple(),
           f.landing_position.as_tuple(),f.velocity_m_s,f.status,f.target_id),
 'history':[(r.boundary,r.position.as_tuple(),r.status) for r in h],
 'rng':s._rng_cursor.state},separators=(',',':')))
"""
            env = {"PYTHONPATH": str(ROOT / "src")}
            completed = subprocess.run([sys.executable, "-S", "-c", script,
                str(pending), str(airborne), object_id], cwd=ROOT, env=env,
                capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            restored = json.loads(completed.stdout)

            encounter.step(3)
            flight = projectile.__dict__["_projectile_flight"]
            history = projectile.__dict__["_atomic_projectile_history"]
            self.assertEqual(restored["time"], encounter.time)
            self.assertEqual(restored["id"], projectile.id)
            self.assertEqual(tuple(restored["position"]), projectile.get_position().as_tuple())
            self.assertEqual(restored["flight"], [flight.release_time, flight.impact_time,
                list(flight.release_position.as_tuple()), list(flight.landing_position.as_tuple()),
                list(flight.velocity_m_s), flight.status, flight.target_id])
            self.assertEqual(flight.target_id, target.id)
            self.assertEqual(restored["history"], [[row.boundary,
                list(row.position.as_tuple()), row.status] for row in history])
            self.assertEqual(self._tuplify(restored["rng"]), source._rng_cursor.state)

            continued = GeneratedArenaSession()
            continued.load_encounter_bytes(airborne.read_bytes())
            continued_candidate = continued.active_candidate
            continued_projectile = continued_candidate.universe.get_object_by_id(object_id)
            continued_candidate.encounter.step(1)
            encounter.step(1)
            self.assertIn(projectile.__dict__["_projectile_flight"].impact_outcome,
                          ("hit", "miss"))
            self.assertEqual(continued_candidate.encounter.time, encounter.time)
            self.assertEqual(continued_projectile.get_position(), projectile.get_position())
            self.assertEqual(continued_projectile.__dict__["_projectile_flight"],
                             projectile.__dict__["_projectile_flight"])
            self.assertEqual(tuple(continued_projectile.__dict__["_atomic_projectile_history"]),
                             tuple(projectile.__dict__["_atomic_projectile_history"]))
            self.assertEqual(continued._rng_cursor.state, source._rng_cursor.state)
            impact.write_bytes(continued.save_encounter_bytes())
            verify_impact = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
c=s.active_candidate;o=c.universe.get_object_by_id(sys.argv[2]);t=c.universe.get_object_by_id(sys.argv[3])
f=o.__dict__['_projectile_flight'];h=o.__dict__['_atomic_projectile_history'][-1]
assert f.impact_outcome in ('hit','miss','fatal','target_moved')
assert h.impact_outcome==f.impact_outcome
print(json.dumps({'outcome':f.impact_outcome,'direction':f.miss_direction,
 'hp':t.current.hit_points,'damage':h.impact_damage,'rng':s._rng_cursor.state},separators=(',',':')))
"""
            checked = subprocess.run([sys.executable, "-S", "-c", verify_impact,
                str(impact), object_id, target.id], cwd=ROOT, env=env,
                capture_output=True, text=True, check=False)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            result = json.loads(checked.stdout)
            self.assertEqual(result["outcome"],
                projectile.__dict__["_projectile_flight"].impact_outcome)
            self.assertEqual(result["direction"],
                projectile.__dict__["_projectile_flight"].miss_direction)
            self.assertEqual(result["damage"],
                projectile.__dict__["_atomic_projectile_history"][-1].impact_damage)
            self.assertEqual(result["hp"], target.current.hit_points)
            self.assertEqual(self._tuplify(result["rng"]), continued._rng_cursor.state)

    def test_repeatable_three_process_movement_continuation(self):
        uninterrupted = self._new_moving_session()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "boundary-1.json"
            second = Path(directory) / "boundary-2.json"
            first.write_bytes(uninterrupted.save_encounter_bytes())
            uninterrupted.advance_one_second()
            first.write_bytes(uninterrupted.save_encounter_bytes())

            script_b = """
import pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
s.advance_one_second();pathlib.Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(s.active_candidate.encounter.time)
"""
            env = {"PYTHONPATH": str(ROOT / "src")}
            b = subprocess.run([sys.executable, "-S", "-c", script_b,
                                str(first), str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            self.assertEqual(b.stdout.strip(), "2")

            script_c = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
s.advance_one_second();c=s.active_candidate;e=c.encounter;p=c.participants[0].native.being
print(json.dumps({'time':e.time,'position':p.get_position().as_tuple(),
 'facing':p.hex_facing,'rng':s._rng_cursor.state,
 'target_history':len(p._atomic_target_history),
 'receipt_history':len(e._atomic_interval_history)},separators=(',',':')))
"""
            c = subprocess.run([sys.executable, "-S", "-c", script_c,
                                str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            restored = json.loads(c.stdout)
            uninterrupted.advance_one_second()
            uninterrupted.advance_one_second()
            candidate = uninterrupted.active_candidate
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            self.assertEqual(restored["time"], 3)
            self.assertEqual(tuple(restored["position"]), player.get_position().as_tuple())
            self.assertEqual(restored["facing"], player.hex_facing)
            self.assertEqual(self._tuplify(restored["rng"]), uninterrupted._rng_cursor.state)
            self.assertEqual(restored["target_history"], len(player._atomic_target_history))
            self.assertEqual(restored["receipt_history"], len(encounter._atomic_interval_history))

    def test_repeatable_three_process_continuation_with_ground_objects(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        uninterrupted = self._new_moving_session(ground_loadout_profile=profile)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "objects-boundary-1.json"
            second = Path(directory) / "objects-boundary-2.json"
            first.write_bytes(uninterrupted.save_encounter_bytes())
            uninterrupted.advance_one_second()
            first.write_bytes(uninterrupted.save_encounter_bytes())

            script_b = """
import pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter
assert len(e.non_being_object_list)==8
assert all(len(c.universe.get_object_by_id(i)._atomic_target_history)==1 for i in e.non_being_object_list)
s.advance_one_second();pathlib.Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(e.time)
"""
            env = {"PYTHONPATH": str(ROOT / "src")}
            b = subprocess.run([sys.executable, "-S", "-c", script_b,
                                str(first), str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            self.assertEqual(b.stdout.strip(), "2")

            script_c = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter
ids=list(e.non_being_object_list);objects=[c.universe.get_object_by_id(i) for i in ids]
assert all(len(o._atomic_target_history)==2 for o in objects)
s.advance_one_second()
print(json.dumps({'time':e.time,'ids':ids,'objects':[(o.id,o.type,o.get_position().as_tuple(),len(o._atomic_target_history)) for o in objects], 'rng':s._rng_cursor.state,'receipts':len(e._atomic_interval_history)},separators=(',',':')))
"""
            c = subprocess.run([sys.executable, "-S", "-c", script_c,
                                str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            restored = json.loads(c.stdout)
            uninterrupted.advance_one_second()
            uninterrupted.advance_one_second()
            candidate = uninterrupted.active_candidate
            encounter = candidate.encounter
            universe = candidate.universe
            expected_objects = [universe.get_object_by_id(key)
                                for key in encounter.non_being_object_list]
            self.assertEqual(restored["time"], 3)
            self.assertEqual(restored["ids"], list(encounter.non_being_object_list))
            self.assertEqual(restored["objects"], [
                [obj.id, obj.type, list(obj.get_position().as_tuple()),
                 len(obj._atomic_target_history)] for obj in expected_objects])
            self.assertEqual(self._tuplify(restored["rng"]), uninterrupted._rng_cursor.state)
            self.assertEqual(restored["receipts"], len(encounter._atomic_interval_history))

    def test_pickup_save_load_preserves_action_inventory_and_continuation(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        session = GeneratedArenaSession(root_seed_factory=lambda: 5050,
                                        ground_loadout_profile=profile)
        session.generate({"starting_experience": "10000",
                          "width_cells": "10", "height_cells": "5"})
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        dagger = next(row for row in candidate.ground_objects
                      if row.category == "weapon" and row.native_type_key == "Dagger")
        session.choose_destination({"column": dagger.column, "row": dagger.row,
                                    "rate": "walk", "facing_policy": "turn"})
        for _ in range(20):
            session.advance_one_second()
            if candidate.arena_map.layout.cell_at_position(player.get_position()) == HexAddress(
                    dagger.column, dagger.row):
                break
        else:
            self.fail("native movement did not reach the generated Dagger's hex")
        visible = next(row for row in session.public_view()["entities"]
                       if row["category"] == "object" and row["type"] == "Dagger"
                       and row["cell"] == {"column": dagger.column, "row": dagger.row})
        session.choose_pickup({"handle": visible["handle"]})
        session.advance_one_second()
        self.assertEqual(session.public_view()["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        active = session.active_candidate
        saved = session.save_encounter_bytes()
        restored = GeneratedArenaSession()
        loaded = restored.load_encounter_bytes(saved)
        loaded_candidate = restored.active_candidate
        loaded_being = loaded_candidate.participants[0].native.being
        loaded_dagger = loaded_candidate.universe.get_object_by_id(dagger.native_object_id)
        self.assertEqual(loaded["pickup_action"], {"name": "Pick up", "status": "completed",
                         "outcome": "success"})
        self.assertEqual(loaded["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertIs(type(loaded_dagger), type(active.universe.get_object_by_id(dagger.native_object_id)))
        self.assertEqual(loaded_dagger.id, dagger.native_object_id)
        self.assertEqual(loaded_dagger.parent_container_id, loaded_being.id)
        self.assertIn(loaded_dagger.id, loaded_being.possessions)
        self.assertEqual(len(loaded_candidate.encounter._atomic_interval_history),
                         len(active.encounter._atomic_interval_history))
        destination = next(address for address in loaded_candidate.arena_map.layout.addresses()
                           if address != loaded_candidate.arena_map.layout.cell_at_position(
                               loaded_being.get_position()))
        for current in (session, restored):
            current.choose_destination({"column": destination.column, "row": destination.row,
                                        "rate": "walk", "facing_policy": "turn"})
            current.advance_one_second()
        self.assertEqual(session.active_candidate.participants[0].native.being.get_position(),
                         restored.active_candidate.participants[0].native.being.get_position())
        repeated_session = GeneratedArenaSession()
        repeated = repeated_session.load_encounter_bytes(restored.save_encounter_bytes())
        self.assertEqual(repeated["time_seconds"], restored.active_candidate.encounter.time)
        session.advance_one_second()
        repeated_session.advance_one_second()
        source_candidate = session.active_candidate
        repeated_candidate = repeated_session.active_candidate
        self.assertEqual(repeated_candidate.participants[0].native.being.get_position(),
                         source_candidate.participants[0].native.being.get_position())
        self.assertEqual(repeated_session._rng_cursor.state, session._rng_cursor.state)
        self.assertEqual(len(repeated_candidate.encounter._atomic_interval_history),
                         len(source_candidate.encounter._atomic_interval_history))
        source_dagger = source_candidate.universe.get_object_by_id(dagger.native_object_id)
        repeated_dagger = repeated_candidate.universe.get_object_by_id(dagger.native_object_id)
        self.assertEqual(repeated_dagger.parent_container_id, source_dagger.parent_container_id)
        self.assertEqual(repeated_dagger._atomic_target_history, source_dagger._atomic_target_history)

    def test_pending_draw_save_load_keeps_exact_two_second_boundary(self):
        scenario = json.loads((ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
                              .read_text(encoding="utf-8"))
        source = GeneratedArenaSession(root_seed_factory=lambda: 5050,
                                       authored_draw_scenario=scenario)
        source.generate({"starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = source.active_candidate
        player = candidate.participants[0].native.being
        dagger = candidate.universe.get_object_by_id(player.possessions[0])
        row = next(row for row in source.public_view()["entities"] if row["type"] == "Dagger")
        source.choose_ready_weapon({"handle": row["handle"], "hand": "right hand"})
        source.advance_one_second()
        saved = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        before = restored.load_encounter_bytes(saved)
        self.assertEqual(before["ready_weapon_action"]["status"], "executing")
        self.assertEqual(before["ready_weapon_action"]["seconds_remaining"], 1)
        restored_player = restored.active_candidate.participants[0].native.being
        restored_dagger = restored.active_candidate.universe.get_object_by_id(dagger.id)
        self.assertIsNone(restored_player.current.body_parts["right hand"])
        self.assertEqual(restored_player.possessions, [dagger.id])
        source.advance_one_second()
        after = restored.advance_one_second()
        self.assertEqual(after["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(restored.active_candidate.encounter.time, source.active_candidate.encounter.time)
        self.assertEqual(restored_player.current.body_parts, player.current.body_parts)
        self.assertEqual(restored_player.possessions, [dagger.id])
        self.assertEqual(restored_player.weapons, player.weapons)
        self.assertEqual(restored_dagger.parent_container_id, dagger.parent_container_id)
        self.assertEqual(restored_dagger.current.weight, dagger.current.weight)
        self.assertEqual(restored._rng_cursor.state, source._rng_cursor.state)
        completed_file = restored.save_encounter_bytes()
        completed_restore = GeneratedArenaSession()
        completed = completed_restore.load_encounter_bytes(completed_file)
        completed_player = completed_restore.active_candidate.participants[0].native.being
        completed_dagger = completed_restore.active_candidate.universe.get_object_by_id(dagger.id)
        self.assertEqual(completed["ready_weapon_action"]["status"], "completed")
        self.assertEqual(completed_player.current.body_parts["right hand"], dagger.id)
        self.assertEqual(completed_player.possessions, [dagger.id])
        self.assertEqual(completed_player.weapons, [dagger.id])
        self.assertEqual(completed_dagger.parent_container_id, player.id)

    def test_pending_pickup_save_load_keeps_exact_one_second_boundary(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        # This generated seed places the selected Dagger adjacent to the
        # player with a clear, represented route, so the strict movement
        # validator does not need inferred clearance through other Objects.
        source = GeneratedArenaSession(root_seed_factory=lambda: 6061,
                                       ground_loadout_profile=profile)
        source.generate({"starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = source.active_candidate
        player = candidate.participants[0].native.being
        dagger = next(row for row in candidate.ground_objects
                      if row.category == "weapon" and row.native_type_key == "Dagger")
        source.choose_destination({"column": dagger.column, "row": dagger.row,
                                   "rate": "walk", "facing_policy": "turn"})
        for _ in range(20):
            source.advance_one_second()
            if candidate.arena_map.layout.cell_at_position(player.get_position()) == HexAddress(
                    dagger.column, dagger.row):
                break
        else:
            self.fail("native movement did not reach the generated Dagger's hex")
        visible = next(row for row in source.public_view()["entities"]
                       if row["category"] == "object" and row["type"] == "Dagger"
                       and row["cell"] == {"column": dagger.column, "row": dagger.row})
        source.choose_pickup({"handle": visible["handle"]})
        saved = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        pending = restored.load_encounter_bytes(saved)
        restored_candidate = restored.active_candidate
        restored_player = restored_candidate.participants[0].native.being
        restored_dagger = restored_candidate.universe.get_object_by_id(dagger.native_object_id)
        self.assertEqual(pending["pickup_action"], {"name": "Pick up", "status": "executing",
                         "outcome": None})
        self.assertEqual(restored_player.possessions, [])
        self.assertIsNone(restored_dagger.parent_container_id)
        result = restored.advance_one_second()
        self.assertEqual(result["pickup_action"], {"name": "Pick up", "status": "completed",
                         "outcome": "success"})
        self.assertEqual(restored_player.possessions, [dagger.native_object_id])
        self.assertEqual(restored_dagger.parent_container_id, player.id)
        self.assertIsNone(restored_dagger.get_position())
        self.assertEqual(restored._rng_cursor.state, source._rng_cursor.state)

    def test_run_action_round_trips_as_completed_native_history(self):
        source = GeneratedArenaSession(root_seed_factory=lambda: 7070)
        source.generate({"starting_experience": "10000", "width_cells": "5", "height_cells": "5"})
        accepted = source.choose_run()
        action_id = next(member.action.id for row in
            source.active_candidate.encounter._choice_book._choices.values()
            for member in row.members)
        pending = GeneratedArenaSession()
        pending_view = pending.load_encounter_bytes(source.save_encounter_bytes())
        self.assertEqual(pending_view["player_action"], {
            "name": "Run", "status": "executing", "outcome": None})
        pending.advance_one_second()
        source.advance_one_second()
        outcome = source.public_view()["player_action"]["outcome"]
        self.assertIn(outcome, ("success", "no_movement"))
        expected_action = {"name": "Run", "status": "completed", "outcome": outcome}
        self.assertEqual(pending.public_view()["player_action"], expected_action)
        self.assertEqual(pending.active_candidate.participants[0].native.being.get_position(),
                         source.active_candidate.participants[0].native.being.get_position())
        restored = GeneratedArenaSession()
        loaded = restored.load_encounter_bytes(pending.save_encounter_bytes())
        self.assertEqual(loaded["player_action"], expected_action)
        candidate = restored.active_candidate
        action = candidate.universe.get_event_by_id(action_id)
        self.assertIsNotNone(action)
        self.assertEqual(candidate.encounter.time, source.active_candidate.encounter.time)
        self.assertEqual(len(candidate.encounter._atomic_interval_history),
                         len(source.active_candidate.encounter._atomic_interval_history))
        restored_player = candidate.participants[0].native.being
        source_player = source.active_candidate.participants[0].native.being
        self.assertEqual(restored_player._atomic_target_history,
                         source_player._atomic_target_history)


if __name__ == "__main__":
    unittest.main()
