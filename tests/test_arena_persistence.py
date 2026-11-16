"""Portable generated-Arena save/load integration tests."""
import json
import math
import os
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
from action import Action
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

    def test_current_snapshot_requires_reviewed_per_type_field_schemas(self):
        from arena_native_snapshot import ArenaNativeSnapshotRejected, encode, restore
        from arena_persistence import decode

        source=GeneratedArenaSession(root_seed_factory=lambda:20261116)
        source.generate({"starting_experience":"10000","width_cells":"5",
                         "height_cells":"5"})
        inventory=decode(source.save_encounter_bytes())["decoded_native"]

        def change_node(tag, transform):
            compatibility,body=inventory
            changed=False
            sections=[]
            for section in body:
                if section[0] != "nodes":
                    sections.append(section)
                    continue
                rows=[]
                for ref,node_tag,content in section[1]:
                    if node_tag == tag and not changed:
                        content=transform(ref,list(content))
                        changed=True
                    rows.append((ref,node_tag,tuple(content)))
                sections.append(("nodes",tuple(rows)))
            self.assertTrue(changed,tag)
            return (compatibility,tuple(sections))

        from checkpoint_fields import FIELD_ADAPTERS
        instance_tag="being.BeingInstance"
        required=next(iter(FIELD_ADAPTERS[instance_tag]["required"]))
        unknown=change_node(instance_tag,
            lambda ref,fields: fields+[("unreviewed_runtime_cache",("none",))])
        missing=change_node(instance_tag,
            lambda ref,fields: [(name,value) for name,value in fields if name != required])
        original_field=next(pair for ref,tag,content in next(
            section for section in inventory[1] if section[0]=="nodes")[1]
            if tag==instance_tag for pair in content if pair[0]==required)
        duplicate=change_node(instance_tag,
            lambda ref,fields: fields+[original_field])
        alien_rows=next(section[1] for section in inventory[1]
                        if section[0]=="nodes")+(("alien-node","unreviewed.Type",()),)
        alien_sections=tuple(("nodes",alien_rows) if section[0]=="nodes" else section
                             for section in inventory[1])
        alien=(inventory[0],alien_sections)
        for label,candidate in (("unknown field",unknown),("missing required",missing),
                                ("duplicate field",duplicate),("unreviewed type",alien)):
            with self.subTest(candidate=label):
                with self.assertRaises(ArenaNativeSnapshotRejected):
                    encode(candidate)
        with self.assertRaises(ArenaNativeSnapshotRejected):
            restore(missing)

    def test_portable_snapshot_omits_rebuilt_quiescent_runtime_fields(self):
        from arena_persistence import decode

        source=GeneratedArenaSession(root_seed_factory=lambda:20261116)
        source.generate({"starting_experience":"10000","width_cells":"5",
                         "height_cells":"5"})
        source.choose_run()
        source.advance_one_second()
        saved=source.save_encounter_bytes()
        inventory=decode(saved)["decoded_native"]
        rows=next(section[1] for section in inventory[1][1:]
                  if section[0]=="nodes")
        fields_by_tag={tag:dict(content) for _ref,tag,content in rows
                       if tag in ("universe.Universe","encounter.Encounter",
                                  "action_choice.ChoiceBook")}
        omitted={
            "universe.Universe":{"_schedule_lock","_reproduction_group_registry"},
            "encounter.Encounter":{"_transactional_mode","_active_fatigue_frame",
                "_boundary_context","_advancing","_running","_dispatching",
                "_coordinator_time","_interval_start","_physiology_registry"},
            "action_choice.ChoiceBook":{"lock","_drafts","_closed_drafts","_tokens"},
        }
        candidate=source.active_candidate
        live_objects={"universe.Universe":candidate.universe,
                      "encounter.Encounter":candidate.encounter,
                      "action_choice.ChoiceBook":candidate.encounter._choice_book}
        for tag,names in omitted.items():
            self.assertTrue(names <= object.__getattribute__(live_objects[tag],"__dict__").keys())
            self.assertTrue(names.isdisjoint(fields_by_tag[tag]))

        restored=GeneratedArenaSession()
        restored.load_encounter_bytes(saved)
        candidate=restored.active_candidate
        world=candidate.universe
        encounter=candidate.encounter
        book=encounter._choice_book
        self.assertIs(book.lock,world._schedule_lock)
        self.assertEqual((book._drafts,book._closed_drafts,book._tokens),({},set(),{}))
        self.assertEqual((encounter._coordinator_time,encounter._interval_start),
                         (encounter.time,encounter.time))
        self.assertFalse(encounter._advancing or encounter._running or encounter._dispatching)
        self.assertEqual(encounter._transactional_mode.name,"transactional")
        self.assertIsNone(encounter._active_fatigue_frame)
        self.assertIsNone(encounter._boundary_context)
        self.assertIsNone(encounter._physiology_registry)
        self.assertEqual(restored.save_encounter_bytes(),saved)

    def test_portable_archive_separates_immutable_definition_table(self):
        import io
        import zipfile
        from arena_history_segments import _DEFINITION_TAGS
        from arena_persistence import decode

        source=GeneratedArenaSession(root_seed_factory=lambda:20261116)
        source.generate({"starting_experience":"10000","width_cells":"5",
                         "height_cells":"5"})
        wire=source.save_encounter_bytes()
        with zipfile.ZipFile(io.BytesIO(wire)) as archive:
            snapshot=json.loads(archive.read("snapshot.json"))
            definitions=json.loads(archive.read("definitions.json"))
        snapshot_rows=snapshot["inventory"][1][2][2][1]
        definition_rows=definitions["nodes"]
        snapshot_tags={row[1] for row in snapshot_rows}
        definition_tags={row[1] for row in definition_rows}
        self.assertTrue(_DEFINITION_TAGS & definition_tags)
        self.assertTrue(_DEFINITION_TAGS.isdisjoint(snapshot_tags))
        snapshot_ids=[row[0] for row in snapshot_rows]
        self.assertTrue(all(ref not in snapshot_ids
                            for ref,_tag in definitions["roots"]))
        self.assertEqual(decode(wire)["decoded_native"],
                         decode(source.save_encounter_bytes())["decoded_native"])
        restored=GeneratedArenaSession()
        restored.load_encounter_bytes(wire)
        self.assertEqual(restored.save_encounter_bytes(),wire)

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

    def test_segmented_portable_archive_is_exact_and_rejects_partial_history_transactionally(self):
        import io
        import zipfile
        from arena_persistence import ArenaSaveRejected, decode
        from unittest.mock import patch

        source=GeneratedArenaSession(root_seed_factory=lambda:20261115)
        source.generate({"starting_experience":"10000","width_cells":"5",
                         "height_cells":"5"})
        source.choose_run()
        source.advance_one_second()
        original_candidate=source.active_candidate
        original=source.save_encounter_bytes()
        native_before=source.active_candidate.encounter.inspect_committed()
        import arena_persistence as portable
        write_entry=portable._write_archive_entry
        def interrupt_export(archive,name,data):
            if name.startswith('history/'):
                raise OSError('injected interruption while building portable archive')
            write_entry(archive,name,data)
        with patch('arena_persistence._write_archive_entry',side_effect=interrupt_export):
            with self.assertRaisesRegex(OSError,'injected interruption'):
                source.save_encounter_bytes()
        self.assertIs(source.active_candidate,original_candidate)
        self.assertEqual(source.active_candidate.encounter.inspect_committed(),native_before)
        self.assertEqual(source.save_encounter_bytes(),original)
        with tempfile.TemporaryDirectory(prefix='arena-save-crash-') as directory:
            prior_path=Path(directory)/'last-complete.uarena'
            prior_path.write_bytes(original)
            crash_script=r'''
import os,sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
import arena_persistence
s=GeneratedArenaSession();s.load_encounter_bytes(Path(sys.argv[1]).read_bytes())
s.choose_delay({'defense':0})
write=arena_persistence._write_archive_entry
def crash_during_new_archive(archive,name,data):
    if name.startswith('history/'):
        os._exit(73)
    write(archive,name,data)
arena_persistence._write_archive_entry=crash_during_new_archive
s.save_encounter_bytes()
raise SystemExit(2)
'''
            environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',
                PYTHONPATH=os.pathsep.join((str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'examples'))))
            killed=subprocess.run([sys.executable,'-B','-c',crash_script,str(prior_path)],
                cwd=ROOT,env=environment,capture_output=True,text=True,timeout=30,check=False)
            self.assertEqual(killed.returncode,73,killed.stderr)
            self.assertEqual(prior_path.read_bytes(),original)
            recovery_script=r'''
import sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
wire=Path(sys.argv[1]).read_bytes();s=GeneratedArenaSession();s.load_encounter_bytes(wire)
assert s.save_encounter_bytes()==wire
Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
'''
            recovered_path=Path(directory)/'recovered.uarena'
            recovered=subprocess.run([sys.executable,'-B','-c',recovery_script,
                str(prior_path),str(recovered_path)],cwd=ROOT,env=environment,
                capture_output=True,text=True,timeout=30,check=False)
            self.assertEqual(recovered.returncode,0,recovered.stderr)
            self.assertEqual(recovered_path.read_bytes(),original)
        parsed=decode(original)
        metrics=parsed["manifest"]["metrics"]
        self.assertEqual(parsed["manifest"]["snapshot_cursor"],1)
        self.assertGreater(metrics["history_segments"],0)
        self.assertLess(metrics["snapshot_nodes"],60_000)
        restored=GeneratedArenaSession()
        restored.load_encounter_bytes(original)
        self.assertEqual(restored.save_encounter_bytes(),original)

        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            entries={name:archive.read(name) for name in archive.namelist()}
        segment_name=next(name for name in entries if name.startswith("history/"))
        corrupted=dict(entries)
        corrupted[segment_name]=corrupted[segment_name]+b" "
        corrupted_definitions=dict(entries)
        corrupted_definitions["definitions.json"] += b" "
        extra=dict(entries)
        extra['history/unlisted-extra.json']=b'{}'
        unsafe_path=dict(entries)
        unsafe_path['../outside.json']=b'{}'

        def archive_bytes(rows):
            output=io.BytesIO()
            with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as archive:
                for name,data in rows.items():
                    archive.writestr(name,data)
            return output.getvalue()

        missing=dict(entries)
        del missing[segment_name]
        missing_definitions=dict(entries)
        del missing_definitions["definitions.json"]
        duplicate_output=io.BytesIO()
        with zipfile.ZipFile(duplicate_output,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            for name,data in entries.items():
                archive.writestr(name,data)
            archive.writestr("snapshot.json",entries["snapshot.json"])
        for label,bad in (("truncated",original[:-12]),
                          ("missing-history-segment",archive_bytes(missing)),
                          ("altered-history-segment",archive_bytes(corrupted)),
                          ("missing-definitions",archive_bytes(missing_definitions)),
                          ("altered-definitions",archive_bytes(corrupted_definitions)),
                          ("unlisted-extra-entry",archive_bytes(extra)),
                          ("unsafe-path",archive_bytes(unsafe_path)),
                          ("duplicate-entry",duplicate_output.getvalue())):
            with self.subTest(corruption=label):
                with self.assertRaises((ArenaSaveRejected, ArenaBrowserRequestError)):
                    source.load_encounter_bytes(bad)
                self.assertIs(source.active_candidate,original_candidate)
                self.assertEqual(source.active_candidate.encounter.time,1)
                self.assertEqual(source.save_encounter_bytes(),original)

    def test_observer_current_view_and_history_restore_in_fresh_process(self):
        source = GeneratedArenaSession(root_seed_factory=lambda: 20261114)
        source.generate({"starting_experience": "10000",
                         "width_cells": "5", "height_cells": "5"})
        before = source.public_view()
        expected = [{key: value for key, value in row.items() if key != "handle"}
                    for row in before["observation_history"]]
        visible = [{key: value for key, value in row.items() if key != "handle"}
                   for row in before["entities"]]
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "observer-save.json"
            save_path.write_bytes(source.save_encounter_bytes())
            script = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();v=s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
clean=lambda rows:[{k:x for k,x in row.items() if k!='handle'} for row in rows]
print(json.dumps({'time':v['time_seconds'],'history':clean(v['observation_history']),
 'current':clean(v['entities'])},sort_keys=True,separators=(',',':')))
"""
            result = subprocess.run([sys.executable, "-S", "-c", script,
                str(save_path)], cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"),
                "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
                check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        resumed = json.loads(result.stdout)
        self.assertEqual(resumed["time"], before["time_seconds"])
        self.assertEqual(resumed["history"], expected)
        self.assertEqual(resumed["current"], visible)

    def test_observed_motion_interval_survives_fresh_process_save_load(self):
        source = GeneratedArenaSession(root_seed_factory=lambda: 20261115)
        source.generate({"starting_experience": "10000",
                         "width_cells": "5", "height_cells": "5"})
        candidate = source.active_candidate
        player = candidate.participants[0].native.being
        observer = candidate.participants[1].native.being
        origin = candidate.arena_map.layout.cell_at_position(player.get_position())
        destination = next(cell for cell in candidate.arena_map.layout.addresses()
                           if cell != origin)
        source.choose_destination({"column": destination.column, "row": destination.row,
                                   "rate": "sprint", "facing_policy": "turn"})
        source.advance_one_second()
        observed = [row for row in observer._arena_perception_ledger.history
                    if row.entity_id == player.id and row.boundary == 1]
        self.assertEqual(len(observed), 1)
        expected = observed[0]
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "observer-motion-save.json"
            save_path.write_bytes(source.save_encounter_bytes())
            script = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
o=s.active_candidate.participants[1].native.being
r=next(x for x in o._arena_perception_ledger.history
       if x.entity_id==sys.argv[2] and x.boundary==1)
print(json.dumps({'time':s.active_candidate.encounter.time,
 'position':None if r.position is None else r.position.as_tuple(),
 'motion':r.motion_interval,'boundary':r.boundary},sort_keys=True))
"""
            result = subprocess.run([sys.executable, "-S", "-c", script,
                str(save_path), player.id], cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        resumed = json.loads(result.stdout)
        self.assertEqual(resumed["time"], 1)
        self.assertEqual(resumed["position"], list(expected.position.as_tuple()))
        self.assertEqual(resumed["motion"], list(expected.motion_interval))
        self.assertEqual(resumed["boundary"], expected.boundary)

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

    def test_compact_native_graph_ids_reject_corrupt_references_and_types(self):
        import copy
        import hashlib
        from arena_native_snapshot import (ArenaNativeSnapshotRejected,
            _canonical, capture, encode as encode_native, decode as decode_native)

        source = GeneratedArenaSession(root_seed_factory=lambda: 20261115)
        source.generate({"starting_experience": "10000", "width_cells": "5",
                         "height_cells": "5"})
        native_wire = encode_native(capture(source.active_candidate.universe,
            source.active_candidate.encounter, source._rng_cursor))
        native = json.loads(native_wire)
        self.assertEqual(native["schema"], "universe.generated-arena-native-state/5")
        compact = native["inventory"][1]
        self.assertEqual(compact[0], "universe.generated-arena-compact-inventory/1")
        symbols = compact[1]
        body = compact[2]
        nodes = body[2][1]
        self.assertTrue(any(row[0][0] == "owned-node" for row in nodes))

        def reseal(mutator):
            value = copy.deepcopy(native)
            mutator(value)
            body = {key: value[key] for key in value if key != "sha256"}
            value["sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
            return _canonical(value)

        cases = []
        cases.append(lambda value: value["inventory"][1][2][2][1][1].__setitem__(
            0, value["inventory"][1][2][2][1][0][0]))

        def make_dangling(value):
            def visit(row):
                if type(row) is list:
                    if (len(row) == 2 and row[0] == "reference"
                            and type(row[1]) is list and row[1]
                            and row[1][0] == "owned-node"):
                        row[1] = ["owned-node", "f" * 64]
                        return True
                    return any(visit(child) for child in row)
                if type(row) is dict:
                    return any(visit(child) for child in row.values())
                return False
            if not visit(value["inventory"]):
                raise AssertionError("compact native reference fixture was not found")
        cases.append(make_dangling)
        cases.append(lambda value: value["inventory"][1][2][2][1][1][0].__setitem__(
            1, "z" * 64))
        cases.append(lambda value: value["inventory"][1][2][2][1][1].__setitem__(
            1, "unreviewed.Process"))
        cases.append(lambda value: value["inventory"][1][1].__setitem__(
            0, value["inventory"][1][1][1]))

        def make_dangling_symbol(value):
            table = value["inventory"][1][1]
            limit = len(table)
            def visit(row):
                if type(row) is list:
                    for index, child in enumerate(row):
                        if type(child) is int and child < 0:
                            row[index] = -(limit + 1)
                            return True
                        if visit(child):
                            return True
                return False
            if not visit(value["inventory"][1][2]):
                raise AssertionError("compact scalar string reference was not found")
        cases.append(make_dangling_symbol)

        def make_odd_pair_table(value):
            rows = value["inventory"][1][2][2][1]
            row = next(item for item in rows
                       if item[1] == "ordered-map" and item[2])
            row[2].pop()
        cases.append(make_odd_pair_table)
        for mutate in cases:
            with self.subTest(corruption=cases.index(mutate)):
                with self.assertRaises(ArenaNativeSnapshotRejected):
                    decode_native(reseal(mutate))


    def test_pinned_native_v4_schema_migrates_to_current_compact_wire(self):
        import base64
        import hashlib
        from arena_native_snapshot import (_LEGACY_V4_COMPATIBILITY,
            _canonical as native_canonical, capture, encode as encode_native,
            decode as decode_native)
        from arena_persistence import _canonical as save_canonical

        source = GeneratedArenaSession(root_seed_factory=lambda: 20261115)
        source.generate({"starting_experience": "10000", "width_cells": "5",
                         "height_cells": "5"})
        current_inventory = capture(source.active_candidate.universe,
            source.active_candidate.encounter, source._rng_cursor)
        current_wire = encode_native(current_inventory)
        current_inventory = decode_native(current_wire)
        legacy_inventory = (_LEGACY_V4_COMPATIBILITY, current_inventory[1])
        legacy_payload = {"schema": "universe.generated-arena-native-state/4",
                          "compatibility": _LEGACY_V4_COMPATIBILITY,
                          "inventory": legacy_inventory}
        legacy_wire = native_canonical(dict(legacy_payload,
            sha256=hashlib.sha256(native_canonical(legacy_payload)).hexdigest()))
        outer_payload = {"schema": "universe.generated-arena-save/8",
            "native_state_base64": base64.b64encode(legacy_wire).decode("ascii"),
            "session": __import__('arena_persistence')._session_record(source,current_wire)}
        legacy_save = save_canonical(dict(outer_payload,
            sha256=hashlib.sha256(save_canonical(outer_payload)).hexdigest()))

        restored = GeneratedArenaSession()
        restored.load_encounter_bytes(legacy_save)
        migrated = restored.save_encounter_bytes()
        self.assertTrue(migrated.startswith(b"PK\x03\x04"))
        self.assertEqual(restored.active_candidate.encounter.time, 0)

    def test_supported_segmented_v10_archive_migrates_in_fresh_process(self):
        from arena_persistence import decode

        legacy=ROOT/"tests/fixtures/arena/legacy-per-scale-010-v10.uarena"
        raw=legacy.read_bytes()
        self.assertEqual(decode(raw)["manifest"]["save_schema"],
                         "universe.generated-arena-save/10")
        with tempfile.TemporaryDirectory(prefix="arena-v10-migration-") as directory:
            migrated=Path(directory)/"migrated.uarena"
            script="""import sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
source=Path(sys.argv[1]).read_bytes(); session=GeneratedArenaSession()
view=session.load_encounter_bytes(source)
assert view['time_seconds']==0
Path(sys.argv[2]).write_bytes(session.save_encounter_bytes())
"""
            environment=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",
                PYTHONNOUSERSITE="1",PYTHONPATH=os.pathsep.join(
                    (str(ROOT/"tests"),str(ROOT/"src"),str(ROOT/"examples"))))
            result=subprocess.run([sys.executable,"-B","-c",script,str(legacy),
                str(migrated)],cwd=ROOT,env=environment,capture_output=True,
                text=True,timeout=60,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            current=migrated.read_bytes()
            self.assertNotEqual(current,raw)
            self.assertEqual(decode(current)["manifest"]["save_schema"],
                             "universe.generated-arena-save/11")


    def test_extended_seed14_combat_checkpoint_stays_strict_and_continues_exactly(self):
        """The former 67-second combat overflow resumes exactly in a new OS process."""
        from arena_persistence import decode as decode_save
        profile = json.loads((ROOT / "tests/fixtures/arena/uact-full-002-one-shield.json").read_text())
        source = GeneratedArenaSession(root_seed_factory=lambda: 14,
                                       ground_loadout_profile=profile)
        source.generate({"starting_experience": "10000", "width_cells": "10",
                         "height_cells": "5", "equipment_mode": "equipped",
                         "opponent_strategy": "attack_only", "root_seed": "14"})
        candidate = source.active_candidate
        encounter = candidate.encounter
        player, opponent = (row.native.being for row in candidate.participants)

        def checkpoint():
            wire = source.save_encounter_bytes()
            parsed = decode_save(wire)
            metrics = parsed["manifest"]["metrics"]
            return {"wire": wire, "outer_bytes": len(wire),
                    "native_bytes": metrics["snapshot_bytes"]+metrics["definitions_bytes"]+metrics["history_bytes"],
                    "nodes": metrics["aggregate_document_nodes"],
                    "snapshot_nodes": metrics["snapshot_nodes"],
                    "snapshot_bytes": metrics["snapshot_bytes"],
                    "definitions_nodes": metrics["definitions_nodes"],
                    "definitions_bytes": metrics["definitions_bytes"],
                    "history_bytes": metrics["history_bytes"],
                    "history_segments": metrics["history_segments"],
                    "history_field_entries": metrics["history_field_entries"],
                    "depth": max(metrics["snapshot_depth"],
                                 metrics["history_max_depth"]),
                    "receipts": len(getattr(encounter, "_atomic_interval_history", ())),
                    "actions": len(source._all_melee_actions(candidate)),
                    "pending_actions": len(encounter.pending_action_list),
                    "completed_actions": len(encounter.finished_action_list)}

        checkpoints = {0: checkpoint()}
        placement = candidate.ground_objects[0]
        destination = HexAddress(placement.column, placement.row)
        source.choose_destination({"column": destination.column, "row": destination.row,
                                   "rate": "walk", "facing_policy": "turn"})
        while (encounter.time < 1
               or candidate.arena_map.layout.cell_at_position(player.get_position()) != destination):
            source.advance_one_second()
        visible = next(row for row in source.public_view()["entities"]
                       if row["name"] == "Small shield")
        shield_id = placement.native_object_id
        source.choose_pickup({"handle": visible["handle"]})
        source.advance_one_second()
        source.advance_one_second()
        visible = next(row for row in source.public_view()["entities"]
                       if row["name"] == "Small shield")
        source.choose_shield_equipment({"handle": visible["handle"],
                                        "hand": "left hand", "operation": "don"})

        for boundary in (10, 20, 35, 50, 67):
            while encounter.time < boundary:
                source.advance_one_second()
            checkpoints[boundary] = checkpoint()
            self.assertLess(checkpoints[boundary]["snapshot_nodes"], 1_000_000,
                            f"resumable snapshot exceeds its per-document limit at t={boundary}")

        self.assertEqual(encounter.time, 67)
        self.assertEqual(len(encounter._atomic_interval_history), 67)
        self.assertEqual(len(source._all_melee_actions(candidate)), 16)
        self.assertEqual((player.get_hit_points(), opponent.get_hit_points()), (9, 17))
        shield = candidate.universe.get_object_by_id(shield_id)
        self.assertIn(shield_id, player.possessions)
        self.assertIn(shield_id, player.current.body_parts.values())
        self.assertTrue(all(row.native.being._arena_perception_ledger.history
                            for row in candidate.participants))
        self.assertGreater(checkpoints[67]["nodes"], checkpoints[35]["nodes"])

        with tempfile.TemporaryDirectory(prefix="arena-long-checkpoint-") as directory:
            save_path = Path(directory) / "t67.json"
            resumed_path = Path(directory) / "resumed.json"
            save_path.write_bytes(checkpoints[67]["wire"])
            script = """
import json,sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter
assert e.time==67 and len(e._atomic_interval_history)==67
p,o=(row.native.being for row in c.participants);ids=(p.id,o.id)
for _ in range(5):s.advance_one_second()
Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(json.dumps({'time':e.time,'receipts':len(e._atomic_interval_history),
 'ids':ids,'hp':(p.get_hit_points(),o.get_hit_points())},sort_keys=True))
"""
            child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                             PYTHONNOUSERSITE="1",
                             PYTHONPATH=os.pathsep.join((str(ROOT / "tests"),
                                 str(ROOT / "src"), str(ROOT / "examples"))))
            result = subprocess.run([sys.executable, "-B", "-c", script,
                str(save_path), str(resumed_path)], cwd=ROOT, env=child_env,
                capture_output=True, text=True, timeout=180, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            resumed = json.loads(result.stdout)
            for _ in range(5):
                source.advance_one_second()
            self.assertEqual(resumed_path.read_bytes(), source.save_encounter_bytes())
        self.assertEqual(resumed["time"], 72)
        self.assertEqual(resumed["receipts"], 72)
        self.assertEqual(tuple(resumed["ids"]), (player.id, opponent.id))
        # The original legal combat cannot reach 64 attacks: continue without
        # altering either Being or the adopted attack-only strategy and prove
        # that ordinary combat kills the player first. Its t=67 history above
        # is already the same/larger payload that exceeded the old cap.
        while (len(source._all_melee_actions(candidate)) < 64
               and player.get_hit_points() > 0 and opponent.get_hit_points() > 0
               and encounter.time < 1000):
            source.advance_one_second()
        self.assertEqual(encounter.time, 91)
        self.assertEqual(len(source._all_melee_actions(candidate)), 22)
        self.assertEqual((player.get_hit_points(), opponent.get_hit_points()), (-2, 17))
        checkpoints[91] = checkpoint()
        self.assertLess(checkpoints[91]["snapshot_nodes"], 1_000_000)
        self.assertLess(checkpoints[91]["nodes"], 10_000_000)

        def fresh_process_roundtrip(boundary, steps):
            with tempfile.TemporaryDirectory(prefix=f"arena-checkpoint-t{boundary}-") as directory:
                input_path = Path(directory) / "checkpoint.json"
                restored_path = Path(directory) / "restored.json"
                continued_path = Path(directory) / "continued.json"
                input_path.write_bytes(checkpoints[boundary]["wire"])
                script = """
import json,sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter
assert e.time==int(sys.argv[3])
Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
for _ in range(int(sys.argv[4])):s.advance_one_second()
Path(sys.argv[5]).write_bytes(s.save_encounter_bytes())
print(json.dumps({'time':e.time,'receipts':len(e._atomic_interval_history),
 'ids':[p.native.being.id for p in c.participants],
 'hp':[p.native.being.get_hit_points() for p in c.participants],
 'actions':len(s._all_melee_actions(c)),
 'observer_histories':[len(p.native.being._arena_perception_ledger.history)
                       for p in c.participants]},sort_keys=True))
"""
                environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                    PYTHONNOUSERSITE="1", PYTHONPATH=os.pathsep.join(
                        (str(ROOT / "tests"), str(ROOT / "src"), str(ROOT / "examples"))))
                result = subprocess.run([sys.executable, "-B", "-c", script,
                    str(input_path), str(restored_path), str(boundary), str(steps),
                    str(continued_path)], cwd=ROOT, env=environment,
                    capture_output=True, text=True, timeout=240, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(restored_path.read_bytes(), input_path.read_bytes())
                return continued_path.read_bytes(), json.loads(result.stdout)

        # Strict reload at the former terminal failure boundary, then continue
        # one ordinary second and compare the complete canonical checkpoint.
        continued, terminal_view = fresh_process_roundtrip(91, 1)
        self.assertEqual(terminal_view["time"], 92)
        source.advance_one_second()
        self.assertEqual(continued, source.save_encounter_bytes())
        checkpoints[92] = checkpoint()

        while encounter.time < 100:
            source.advance_one_second()
        checkpoints[100] = checkpoint()
        self.assertEqual(checkpoints[100]["snapshot_nodes"],
                         checkpoints[91]["snapshot_nodes"])
        self.assertGreater(checkpoints[100]["history_bytes"],
                           checkpoints[91]["history_bytes"])
        continued, later_view = fresh_process_roundtrip(100, 1)
        self.assertEqual(later_view["time"], 101)
        source.advance_one_second()
        self.assertEqual(continued, source.save_encounter_bytes())
        self.assertEqual(later_view["receipts"], 101)
        self.assertEqual(later_view["ids"], [player.id, opponent.id])
        if os.environ.get("UNIVERSE_PER_SCALE_METRICS"):
            print("U-PER-SCALE-METRICS " + json.dumps({
                str(boundary): {key: value for key, value in row.items()
                                if key != "wire"}
                for boundary, row in checkpoints.items()}, sort_keys=True))

    def test_native_world_registry_persistence_size_curve_2_20_200(self):
        """Measure supported, unplaced world-Beings without inventing participant facts."""
        script = r'''
import json,resource,sys,time
from pathlib import Path
mode,size,path,resaved=sys.argv[1],int(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4])
from arena_browser_session import GeneratedArenaSession
from being import BeingInstance
from weapon import WeaponInstance
if mode == "create":
    session=GeneratedArenaSession(root_seed_factory=lambda:20261115)
    session.generate({'starting_experience':'10000','width_cells':'5','height_cells':'5'})
    candidate=session.active_candidate
    base=candidate.participants[0].native.being
    world=candidate.universe
    weapon_definition=world.get_weapon_definition('Dagger')
    assert weapon_definition is not None
    started=time.perf_counter()
    for index in range(size-2):
        ordinal=index+1
        being=BeingInstance(base.original,name=f'Unplaced world Being {ordinal:03d}',
            id=f'per-scale/world-being/{ordinal:03d}')
        world.add_object(being)
        weapon=WeaponInstance(weapon_definition,name=f'World Dagger {ordinal:03d}')
        weapon.id=f'per-scale/world-dagger/{ordinal:03d}'
        world.add_object(weapon)
        being.weapons.append(weapon.id)
    create_seconds=time.perf_counter()-started
    started=time.perf_counter();wire=session.save_encounter_bytes();save_seconds=time.perf_counter()-started
    path.write_bytes(wire)
    from arena_persistence import decode
    metrics=decode(wire)['manifest']['metrics']
    print(json.dumps({'mode':'create','beings':size,'extra_weapons':size-2,
      'snapshot_nodes':metrics['snapshot_nodes'],'snapshot_bytes':metrics['snapshot_bytes'],
      'definitions_nodes':metrics['definitions_nodes'],'definitions_bytes':metrics['definitions_bytes'],
      'history_bytes':metrics['history_bytes'],
      'archive_bytes':len(wire),'create_seconds':create_seconds,'save_seconds':save_seconds,
      'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},sort_keys=True))
elif mode == "load":
    wire=path.read_bytes();session=GeneratedArenaSession();started=time.perf_counter()
    session.load_encounter_bytes(wire);load_seconds=time.perf_counter()-started
    candidate=session.active_candidate
    beings=[row for row in candidate.universe.object_registry.object_instances.values()
            if type(row) is BeingInstance]
    weapons=[row for row in candidate.universe.object_registry.object_instances.values()
             if type(row) is WeaponInstance]
    assert len(beings)==size and len(weapons)==size-2,(len(beings),len(weapons))
    started=time.perf_counter();again=session.save_encounter_bytes();resave_seconds=time.perf_counter()-started
    assert again==wire
    resaved.write_bytes(again)
    print(json.dumps({'mode':'load','beings':len(beings),'weapons':len(weapons),
      'load_seconds':load_seconds,'resave_seconds':resave_seconds,
      'exact_resave':True,'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},sort_keys=True))
else: raise AssertionError(mode)
'''
        measurements=[]
        environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',
            PYTHONPATH=os.pathsep.join((str(ROOT/'tests'),str(ROOT/'src'),str(ROOT/'examples'))))
        with tempfile.TemporaryDirectory(prefix='arena-world-size-') as directory:
            root=Path(directory)
            for size in (2,20,200):
                input_path=root/f'{size}.uarena'
                resaved_path=root/f'{size}-resaved.uarena'
                outputs=[]
                for mode in ('create','load'):
                    process=subprocess.run([sys.executable,'-B','-c',script,mode,str(size),
                        str(input_path),str(resaved_path)],cwd=ROOT,env=environment,
                        capture_output=True,text=True,timeout=240,check=False)
                    self.assertEqual(process.returncode,0,process.stderr)
                    outputs.append(json.loads(process.stdout.strip().splitlines()[-1]))
                self.assertEqual(input_path.read_bytes(),resaved_path.read_bytes())
                self.assertEqual(outputs[0]['beings'],size)
                self.assertEqual(outputs[1]['beings'],size)
                self.assertTrue(outputs[1]['exact_resave'])
                measurements.append({'beings':size,'create_save':outputs[0],
                                     'fresh_process_load':outputs[1]})
        if os.environ.get('UNIVERSE_PER_SCALE_METRICS') == '1':
            print('U-PER-SCALE-WORLD-METRICS '+json.dumps(measurements,sort_keys=True))

    def test_64_lawful_native_feint_resolutions_segment_history_and_resume(self):
        """A generated Arena can retain and continue more than 64 native combat Actions."""
        profile = json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text())
        source = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                       ground_loadout_profile=profile)
        source.generate({"starting_experience": "5000000", "width_cells": "10",
                         "height_cells": "5", "equipment_mode": "equipped",
                         "opponent_strategy": "none"})
        # Prepublication scenario setup uses represented continuous positions
        # from the native Arena map so each Feint reaches the Attack Roll.
        from spatial.state import CartesianPosition
        from hex_facing import nearest_facing
        candidate = source.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        origin = player.get_position()
        target.set_position(CartesianPosition(origin.x + 0.2, origin.y, origin.z))
        player.set_hex_facing(nearest_facing((1.0, 0.0, 0.0)))
        candidate.encounter.difficulty_class = 1
        source.choose_run()
        source.advance_one_second()
        candidate = source.active_candidate
        encounter = candidate.encounter
        player, target = (row.native.being for row in candidate.participants)
        handle = source._view_handles[target.id]

        def resolve_feint():
            ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
            evidence = next(row for row in ledger.current if row.entity_id == target.id)
            action, prepared = source._feint_preflight(
                candidate, player, target.id, evidence, "thrust")
            sequence = 1 + sum(
                type(event) is Action and event.event_type == "feint"
                and event.actor_id == player.id
                for event in candidate.universe.event_history.values())
            action.id = f"{encounter.id}/arena-player-feint/{sequence}"
            source._selected_entity_handle = handle
            encounter.schedule_action(action)
            self.assertNotIn(action.id, encounter.finished_action_list)
            encounter.step(int(prepared.end_time - encounter.time))
            self.assertIn(action.id, encounter.finished_action_list)
            return action

        actions = [resolve_feint() for _ in range(64)]
        feint_ids = {action.id for action in actions}
        self.assertEqual(len(feint_ids), 64)
        self.assertTrue(feint_ids <= set(encounter.finished_action_list))
        committed = encounter.inspect_committed(encounter.time)
        for action in actions:
            receipt = committed.action(action.id)
            self.assertEqual(receipt.lifecycle.status, "finished")
            self.assertIn(receipt.facts.outcome, ("success", "failure"))
            self.assertAlmostEqual(dict(receipt.facts.metadata)["distance"], 0.2)
        self.assertEqual((player.get_hit_points(), target.get_hit_points()),
                         (81, 97))
        at_64 = source.save_encounter_bytes()
        from arena_persistence import decode as decode_save
        parsed = decode_save(at_64)
        metrics = parsed["manifest"]["metrics"]
        self.assertEqual(parsed["manifest"]["snapshot_cursor"], encounter.time)
        self.assertLess(metrics["snapshot_nodes"], 1_000_000)
        self.assertEqual(metrics["history_segments"], encounter.time)
        self.assertEqual(metrics["history_field_entries"][
            "encounter.Encounter._atomic_interval_history"], encounter.time)
        # Shared immutable interval projections materially reduce the prior
        # count while retaining the full 64-Action receipt history.
        self.assertGreater(metrics["history_wire_nodes"], 400_000)

        def advance_one_more(session):
            candidate = session.active_candidate
            player = candidate.participants[0].native.being
            target = candidate.participants[1].native.being
            handle = session._view_handles[target.id]
            view = session.choose_feint({"handle": handle, "motion": "thrust"})
            action = session._player_feint_action(candidate, player)
            while view["feint_action"]["status"] == "executing":
                view = session.advance_one_second()
            return action

        with tempfile.TemporaryDirectory(prefix="arena-64-actions-") as directory:
            input_path = Path(directory) / "64-actions.uarena"
            restored_path = Path(directory) / "restored.uarena"
            continued_path = Path(directory) / "continued.uarena"
            input_path.write_bytes(at_64)
            script = """
import json,sys
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();raw=Path(sys.argv[1]).read_bytes();s.load_encounter_bytes(raw)
assert s.save_encounter_bytes()==raw
c=s.active_candidate;e=c.encounter;p,t=(r.native.being for r in c.participants)
ids=[p.id,t.id]
v=s.choose_feint({'handle':s._view_handles[t.id],'motion':'thrust'})
a=s._player_feint_action(c,p)
while v['feint_action']['status']=='executing':v=s.advance_one_second()
Path(sys.argv[2]).write_bytes(raw)
Path(sys.argv[3]).write_bytes(s.save_encounter_bytes())
print(json.dumps({'time':e.time,'receipts':len(e._atomic_interval_history),
 'ids':ids,'action_id':a.id,'feints':sum(1 for x in e.finished_action_list
 if getattr(c.universe.get_event_by_id(x),'event_type',None)=='feint'),
 'hp':[p.get_hit_points(),t.get_hit_points()]},sort_keys=True))
"""
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                PYTHONNOUSERSITE="1", PYTHONPATH=os.pathsep.join(
                    (str(ROOT / "tests"), str(ROOT / "src"), str(ROOT / "examples"))))
            result = subprocess.run([sys.executable, "-B", "-c", script,
                str(input_path), str(restored_path), str(continued_path)], cwd=ROOT,
                env=environment, capture_output=True, text=True, timeout=240,
                check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            continued = json.loads(result.stdout)
            restored_bytes=restored_path.read_bytes()
            if restored_bytes != at_64:
                import io,zipfile
                def archive_rows(wire):
                    with zipfile.ZipFile(io.BytesIO(wire)) as archive:
                        return {name:archive.read(name) for name in archive.namelist()}
                before_rows=archive_rows(at_64)
                after_rows=archive_rows(restored_bytes)
                changed=[]
                for name in sorted(set(before_rows)|set(after_rows)):
                    if before_rows.get(name)==after_rows.get(name):
                        continue
                    detail=name
                    if name in before_rows and name in after_rows and name.endswith('.json'):
                        try:
                            before_json=json.loads(before_rows[name])
                            after_json=json.loads(after_rows[name])
                            if name=='snapshot.json':
                                before_nodes=before_json['inventory'][2][2][1]
                                after_nodes=after_json['inventory'][2][2][1]
                                detail+=f" snapshot_nodes={len(before_nodes)}/{len(after_nodes)}"
                                detail+=f" snapshot_equal={before_json==after_json}"
                            else:
                                detail+=f" json_equal={before_json==after_json}"
                        except (KeyError,TypeError,ValueError):
                            pass
                    changed.append(detail)
                self.fail('fresh-process exact resave changed archive members: '
                          + ', '.join(changed[:12]))
            action = advance_one_more(source)
            self.assertEqual(continued_path.read_bytes(), source.save_encounter_bytes())
        self.assertEqual(continued["time"], encounter.time)
        self.assertEqual(continued["receipts"], encounter.time)
        self.assertEqual(continued["ids"], [player.id, target.id])
        self.assertEqual(continued["action_id"], action.id)
        self.assertEqual(continued["feints"], 65)
        self.assertEqual(continued["hp"], [81, 97])
        at_65 = decode_save(source.save_encounter_bytes())
        at_65_metrics = at_65["manifest"]["metrics"]
        # After a burst of Actions, hold the represented world steady for 169
        # legal native quiet boundaries. Only current time and committed
        # history advance; the resume snapshot must plateau.
        for _ in range(169):
            encounter.step(1)
        self.assertEqual(encounter.time, 300)
        quiet_receipts = encounter._atomic_interval_history
        self.assertIs(quiet_receipts[130].inspection.entities,
                      quiet_receipts[299].inspection.entities)
        self.assertIsNot(quiet_receipts[130].inspection,
                         quiet_receipts[299].inspection)
        self.assertNotEqual(quiet_receipts[130].inspection.actions,
                            quiet_receipts[299].inspection.actions)
        self.assertEqual(quiet_receipts[299].inspection.end, 300)
        targets_with_history = [obj for obj in candidate.universe.object_registry.object_instances.values()
                                if obj.__dict__.get("_atomic_target_history")]
        self.assertTrue(targets_with_history)
        for obj in targets_with_history:
            history = obj.__dict__["_atomic_target_history"]
            # Boundary 131 carries the just-finished Feint's outgoing effect
            # identities. From the following quiet boundary onward, unchanged
            # target projections are structurally shared exactly.
            self.assertIs(history[131].state, history[299].state)
        import time
        save_started = time.perf_counter()
        at_300_wire = source.save_encounter_bytes()
        save_seconds = time.perf_counter() - save_started
        at_300 = decode_save(at_300_wire)
        at_300_metrics = at_300["manifest"]["metrics"]
        from arena_history_segments import split as split_history
        _, _, _, history_attribution = split_history(
            at_300["decoded_native"], include_diagnostics=True)
        self.assertEqual(at_300["manifest"]["snapshot_cursor"], 300)
        self.assertEqual(at_300_metrics["snapshot_nodes"], at_65_metrics["snapshot_nodes"])
        self.assertEqual(at_300_metrics["snapshot_bytes"], at_65_metrics["snapshot_bytes"])
        self.assertEqual(at_300_metrics["history_segments"], 300)
        self.assertEqual(at_300_metrics["history_field_entries"][
            "encounter.Encounter._atomic_interval_history"], 300)
        self.assertGreater(at_300_metrics["history_bytes"], at_65_metrics["history_bytes"])
        self.assertEqual((player.get_hit_points(), target.get_hit_points()), (81, 97))
        with tempfile.TemporaryDirectory(prefix="arena-300-quiet-") as directory:
            path = Path(directory) / "t300.uarena"
            output = Path(directory) / "t301.uarena"
            path.write_bytes(at_300_wire)
            script = """import sys
import json,time
from pathlib import Path
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();raw=Path(sys.argv[1]).read_bytes();started=time.perf_counter();s.load_encounter_bytes(raw)
assert s.save_encounter_bytes()==raw
s.active_candidate.encounter.step(1)
Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(json.dumps({'load_and_resave_seconds':time.perf_counter()-started},sort_keys=True))
"""
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                PYTHONNOUSERSITE="1", PYTHONPATH=os.pathsep.join(
                    (str(ROOT / "tests"), str(ROOT / "src"), str(ROOT / "examples"))))
            result = subprocess.run([sys.executable, "-B", "-c", script,
                str(path), str(output)], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=240, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            load_metrics = json.loads(result.stdout)
            encounter.step(1)
            self.assertEqual(output.read_bytes(), source.save_encounter_bytes())
        import resource
        if os.environ.get("UNIVERSE_PER_SCALE_METRICS"):
            print("U-PER-SCALE-64-METRICS " + json.dumps({
                "t64": metrics,
                "t65": at_65_metrics,
                "t300": at_300_metrics,
                "t300_outer_archive_bytes": len(at_300_wire),
                "t300_history_category_owned_rows": history_attribution[
                    "history_category_owned_rows"],
                "t300_history_category_owned_row_bytes": history_attribution[
                    "history_category_owned_row_bytes"],
                "t300_snapshot_category_rows": history_attribution[
                    "snapshot_category_rows"],
                "t300_snapshot_category_row_bytes": history_attribution[
                    "snapshot_category_row_bytes"],
                "t300_save_seconds": save_seconds,
                "fresh_process_load_and_resave_seconds": load_metrics["load_and_resave_seconds"],
                "process_peak_rss_platform_units": resource.getrusage(
                    resource.RUSAGE_SELF).ru_maxrss,
            }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
