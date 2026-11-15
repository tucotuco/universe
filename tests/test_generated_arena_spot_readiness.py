"""Geometry and Encounter-initiation readiness proofs for generated Arena Spot."""

from pathlib import Path
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from activities import SpotAction
from arena_browser_session import GeneratedArenaSession
from atomic_publication import RNGCursor
from encounter import Encounter
from generated_arena_spot_geometry import run_case
from library import Library


class TestGeneratedArenaSpotReadiness(unittest.TestCase):
    def _session(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        state = session.generate({
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(state["state"], "active")
        return session

    def test_generated_candidate_has_no_supported_production_geometry_mapping(self):
        library = Library(config_dir=str(ROOT / "src/config"))
        for race in ("Human", "Grey elf", "High elf", "Wood elf", "Half-elf"):
            definition = library.get_being_definition(race)
            with self.subTest(race=race):
                self.assertIsNotNone(definition)
                self.assertEqual((definition.width, definition.height), (0, 0))
                # Current generated definitions carry empty hand slots, but
                # still do not provide a physical shape or ray-intersection model.
                self.assertTrue(set(definition.body_parts).issubset(
                    {"left hand", "right hand"}))
                self.assertTrue(all(value is None for value in definition.body_parts.values()))
                self.assertFalse(hasattr(definition, "geometry"))

    def test_browser_exposes_only_this_observers_current_view_and_history_handles(self):
        session = self._session()
        candidate = session.active_candidate
        observer, other = (row.native.being for row in candidate.participants)
        view = session.public_view()
        self.assertEqual(len(view["entities"]), 1)
        self.assertEqual(len(view["observation_history"]), 1)
        current = view["entities"][0]
        history = view["observation_history"][0]
        self.assertEqual(history["handle"], current["handle"])
        self.assertEqual(history["name"], current["name"])
        self.assertEqual(history["time_seconds"], 0)
        self.assertNotIn(observer.id, json.dumps(history))
        self.assertNotIn(other.id, json.dumps(history))
        catalog = {row["name"]: row for row in view["action_catalog"]["entries"]}
        self.assertEqual(catalog["Search"]["status"], "unavailable")
        self.assertEqual(catalog["Listen"]["status"], "unavailable")
        self.assertEqual(catalog["Spot"]["status"], "unavailable")
        from examples.arena_web import _GENERATED_PAGE
        self.assertIn('id="observationHistorySection"', _GENERATED_PAGE)
        self.assertIn("function renderObservationHistory(s)", _GENERATED_PAGE)

    def test_committed_movement_opens_one_incidental_visual_discovery_opportunity(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 73111,
            default_equipment_mode="equipped")
        session.generate({"starting_experience": "10000", "width_cells": "5",
            "height_cells": "5", "root_seed": "73111", "opponent_strategy": "none",
            "authored_scenario": "arena-spot-demo"})
        candidate = session.active_candidate
        observer, target = (row.native.being for row in candidate.participants)
        self.assertNotIn(target.id, candidate.encounter.aware_beings(observer.id))
        self.assertFalse(any(row.entity_id == target.id
            for row in observer._arena_perception_ledger.history))

        # This committed movement clears the fixture's explicitly authored
        # opaque screen. Initial-Arena passive perception supplies the
        # incidental evidence at the movement boundary; no Spot retry runs.
        session.choose_destination({"column": 2, "row": 0, "rate": "walk",
                                    "facing_policy": "turn"})
        result = session.advance_one_second()
        self.assertIn(target.id, candidate.encounter.aware_beings(observer.id))
        self.assertIn(observer.id, candidate.encounter.aware_beings(target.id))
        evidence = next(row for row in observer._arena_perception_ledger.history
                        if row.entity_id == target.id)
        self.assertEqual((evidence.boundary, evidence.time, evidence.currently_observable),
                         (1, 1.0, True))
        self.assertIn(target.name, json.dumps(result))
        self.assertFalse(any(getattr(event, "event_type", None) in ("spot", "search", "listen")
            for event in candidate.universe.event_history.values()))
        self.assertEqual(len([event for event in candidate.universe.event_history.values()
            if getattr(event, "event_type", None) in ("spot", "search", "listen")]), 0)
        session.advance_one_second()
        self.assertIn(target.id, candidate.encounter.aware_beings(observer.id))
        self.assertEqual(len([event for event in candidate.universe.event_history.values()
            if getattr(event, "event_type", None) in ("spot", "search", "listen")]), 0)

    def test_observer_history_records_only_native_committed_motion_segments(self):
        session = self._session()
        candidate = session.active_candidate
        player, observer = (row.native.being for row in candidate.participants)
        origin = candidate.arena_map.layout.cell_at_position(player.get_position())
        destination = next(cell for cell in candidate.arena_map.layout.addresses()
                           if cell != origin)
        session.choose_destination({"column": destination.column, "row": destination.row,
                                    "rate": "sprint", "facing_policy": "turn"})
        session.advance_one_second()
        evidence = next(row for row in observer._arena_perception_ledger.history
                        if row.entity_id == player.id and row.boundary == 1)
        self.assertIsNotNone(evidence.motion_interval)
        self.assertEqual(evidence.motion_interval[0], 0.0)
        self.assertGreater(evidence.motion_interval[1], 0.0)
        self.assertLessEqual(evidence.motion_interval[1], 1.0)
        self.assertTrue(any(evidence.motion_interval[2:]))
        self.assertNotIn(player.id, json.dumps(session.public_view()["observation_history"]))

    def test_initial_passive_evidence_respects_authored_opaque_geometry(self):
        from arena_perception import initialize_arena_perception
        from spatial.geometry import AxisAlignedBox, Sphere
        from spatial.occlusion import VisualOcclusion

        session = self._session()
        candidate = session.active_candidate
        observer, target = (row.native.being for row in candidate.participants)
        start, end = observer.get_position(), target.get_position()
        midpoint = type(start)(*(a + (b - a) / 2
                                  for a, b in zip(start.as_tuple(), end.as_tuple())))
        wall_id = candidate.universe.make_object("Brick", "Authored opaque test wall")
        wall = candidate.universe.get_object_by_id(wall_id)
        wall.set_position(midpoint)
        wall.set_geometry(AxisAlignedBox(1.0, 2.0, 2.0))
        wall.set_visual_occlusion(VisualOcclusion(1.0))
        target.set_geometry(Sphere(0.25))
        candidate.encounter.add_object(wall_id)

        # This candidate is still unpublished to the Arena caller. Its explicit
        # wall/target shapes are fixture facts, not generated Being anatomy.
        ledgers = initialize_arena_perception(candidate.encounter)
        self.assertEqual(len(ledgers), 2)
        self.assertNotIn(target.id, observer._arena_perception_ledger._current)
        self.assertNotIn(target.id, candidate.encounter.aware_beings(observer.id))
        self.assertNotIn(target.id, [row.entity_id
            for row in observer._arena_perception_ledger.history])
        self.assertNotIn(observer.id, target._arena_perception_ledger._current)

    def test_authored_spot_refuses_blocked_path_and_restores_fresh_process(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 73111)
        initial = session.generate({
            "starting_experience": "10000", "width_cells": "5", "height_cells": "5",
            "root_seed": "73111", "opponent_strategy": "none",
            "authored_scenario": "arena-spot-demo"})
        candidate = session.active_candidate
        player, hidden = (row.native.being for row in candidate.participants)
        self.assertNotIn(hidden.id, candidate.encounter.aware_beings(player.id))
        self.assertNotIn(hidden.name, json.dumps(initial))
        self.assertEqual(len(initial["entities"]), 1)
        self.assertFalse(initial["spot_available"])

        session.choose_run()
        session.advance_one_second()
        from arena_perception import modeled_sightline_blocked
        self.assertTrue(modeled_sightline_blocked(candidate.encounter, player.id, hidden.id))
        self.assertNotIn(hidden.id, candidate.encounter.aware_beings(player.id))
        self.assertTrue(session.public_view()["spot_available"])

        accepted = session.choose_spot({})
        self.assertEqual(accepted["spot_action"]["status"], "executing")
        self.assertNotIn(hidden.id, json.dumps(accepted))
        self.assertNotIn(hidden.name, json.dumps(accepted))
        for _ in range(6):
            result = session.advance_one_second()
        self.assertEqual(result["spot_action"]["outcome"], "no_clear_path")
        self.assertNotIn(hidden.id, candidate.encounter.aware_beings(player.id))
        self.assertNotIn(player.id, candidate.encounter.aware_beings(hidden.id))
        self.assertNotIn(hidden.name, json.dumps(result["entities"]))
        self.assertNotIn(hidden.id, json.dumps(result))

        from checkpoint_arena_perception import encode_arena_perception_ledger
        def digest(active_session):
            state = active_session.active_candidate
            evidence = tuple(encode_arena_perception_ledger(
                participant.native.being._arena_perception_ledger,
                observer=participant.native.being, encounter=state.encounter,
                registry=state.universe.object_registry.object_instances)
                for participant in state.participants)
            awareness = tuple((key, tuple(sorted(value)))
                              for key, value in sorted(state.encounter.awareness.items()))
            value = (state.encounter.time, state.encounter.last_processed_boundary,
                awareness, evidence, active_session._rng_cursor.state,
                active_session.public_view()["spot_action"])
            return __import__("hashlib").sha256(repr(value).encode()).hexdigest()

        before_digest = digest(session)
        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "authored-spot.arena"
            save_path.write_bytes(session.save_encounter_bytes())
            code = r'''import hashlib,sys
from arena_browser_session import GeneratedArenaSession
from checkpoint_arena_perception import encode_arena_perception_ledger
s=GeneratedArenaSession();s.load_encounter_bytes(open(sys.argv[1],'rb').read());c=s.active_candidate
e=tuple(encode_arena_perception_ledger(p.native.being._arena_perception_ledger,
 observer=p.native.being,encounter=c.encounter,
 registry=c.universe.object_registry.object_instances) for p in c.participants)
a=tuple((k,tuple(sorted(v))) for k,v in sorted(c.encounter.awareness.items()))
value=(c.encounter.time,c.encounter.last_processed_boundary,a,e,s._rng_cursor.state,
 s.public_view()['spot_action'])
print(hashlib.sha256(repr(value).encode()).hexdigest())'''
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT / "examples"),
                str(ROOT / "tests"), str(ROOT.parent / "npc-generator"), env.get("PYTHONPATH", "")))
            child = subprocess.run([sys.executable, "-S", "-B", "-c", code, str(save_path)],
                cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout.strip(), before_digest)

    def test_authored_search_and_listen_continue_pending_in_fresh_process(self):
        from checkpoint_arena_perception import encode_arena_perception_ledger
        from activities import SpotAction

        def prepare(sense, dc):
            session = GeneratedArenaSession(root_seed_factory=lambda: 73111,
                                            default_equipment_mode='equipped')
            session.generate({'starting_experience': '10000', 'width_cells': '5',
                'height_cells': '5', 'root_seed': '73111', 'opponent_strategy': 'none',
                'authored_scenario': 'arena-spot-demo'})
            candidate = session.active_candidate
            actor, target = (row.native.being for row in candidate.participants)
            target.current.discovery_dc = dc
            # A target-free Run Choice starts the Encounter without moving
            # through the authored screen, keeping the Search/Listen target
            # legitimately unknown until the Action resolves.
            session.choose_run()
            session.advance_one_second()
            hidden = json.dumps(session.public_view())
            self.assertNotIn(target.id, hidden)
            self.assertNotIn(target.name, hidden)
            accepted = session.choose_discovery({'sense': sense})
            self.assertNotIn(target.id, json.dumps(accepted))
            self.assertNotIn(target.name, json.dumps(accepted))
            session.advance_one_second()
            self.assertEqual(candidate.encounter.time, 2)
            return session, actor, target

        def digest(session, sense):
            candidate = session.active_candidate
            ledgers = tuple(encode_arena_perception_ledger(
                row.native.being._arena_perception_ledger,
                observer=row.native.being, encounter=candidate.encounter,
                registry=candidate.universe.object_registry.object_instances)
                for row in candidate.participants)
            action = next(row for row in candidate.universe.event_history.values()
                          if type(row) is SpotAction and row.event_type == sense)
            return __import__('hashlib').sha256(repr((candidate.encounter.time,
                candidate.encounter.last_processed_boundary,
                tuple((key, tuple(sorted(value))) for key, value in
                      sorted(candidate.encounter.awareness.items())), ledgers,
                session._rng_cursor.state, action.resolution.outcome,
                session.public_view()['discovery_actions'][sense])).encode()).hexdigest()

        code = r'''import hashlib,sys
from arena_browser_session import GeneratedArenaSession
from checkpoint_arena_perception import encode_arena_perception_ledger
from activities import SpotAction
s=GeneratedArenaSession();s.load_encounter_bytes(open(sys.argv[1],'rb').read());sense=sys.argv[2]
for _ in range(5):s.advance_one_second()
c=s.active_candidate
ledgers=tuple(encode_arena_perception_ledger(p.native.being._arena_perception_ledger,
 observer=p.native.being,encounter=c.encounter,
 registry=c.universe.object_registry.object_instances) for p in c.participants)
a=next(x for x in c.universe.event_history.values() if type(x) is SpotAction and x.event_type==sense)
value=(c.encounter.time,c.encounter.last_processed_boundary,
 tuple((k,tuple(sorted(v))) for k,v in sorted(c.encounter.awareness.items())),ledgers,
 s._rng_cursor.state,a.resolution.outcome,s.public_view()['discovery_actions'][sense])
print(hashlib.sha256(repr(value).encode()).hexdigest())'''
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'src'), str(ROOT / 'examples'),
            str(ROOT / 'tests'), str(ROOT.parent / 'npc-generator'), env.get('PYTHONPATH', '')))
        for sense in ('search', 'listen'):
            for dc, expected in ((1, 'success'), (100, 'failure')):
                with self.subTest(sense=sense, dc=dc):
                    source, actor, target = prepare(sense, dc)
                    pending_bytes = source.save_encounter_bytes()
                    for _ in range(5):
                        result = source.advance_one_second()
                    self.assertEqual(result['discovery_actions'][sense]['outcome'], expected)
                    self.assertNotIn(actor.id,
                        source.active_candidate.encounter.aware_beings(target.id))
                    if expected == 'failure':
                        self.assertNotIn(target.id, json.dumps(result))
                        self.assertNotIn(target.name, json.dumps(result))
                    before_digest = digest(source, sense)
                    with tempfile.TemporaryDirectory() as tmp:
                        save_path = Path(tmp) / f'{sense}-{dc}.arena'
                        save_path.write_bytes(pending_bytes)
                        child = subprocess.run([sys.executable, '-S', '-B', '-c', code,
                            str(save_path), sense], cwd=ROOT, env=env, capture_output=True,
                            text=True, check=False, timeout=120)
                    self.assertEqual(child.returncode, 0, child.stderr)
                    self.assertEqual(child.stdout.strip(), before_digest)
                    if expected == 'success':
                        self.assertIn(target.id, source.active_candidate.encounter.aware_beings(actor.id))
                    else:
                        self.assertNotIn(target.id, source.active_candidate.encounter.aware_beings(actor.id))

    def test_uninitiated_candidate_cannot_start_target_free_spot_and_refusal_is_atomic(self):
        session = self._session()
        candidate = session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        actor_id, target_id = player.native.being.id, hidden.native.being.id
        hidden.native.being.set_name("Hidden Target Sentinel")
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.initiation)
        self.assertEqual(set(encounter.awareness), {actor_id, target_id})
        self.assertEqual(encounter.aware_beings(actor_id), [target_id])
        self.assertEqual(encounter.aware_beings(target_id), [actor_id])
        self.assertIsNone(player.native.being.geometry)
        self.assertIsNone(hidden.native.being.geometry)
        self.assertFalse(session.public_view()["spot_available"])

        before = (encounter.time, encounter.last_processed_boundary, encounter.initiated,
                  encounter.initiation, dict(encounter.awareness),
                  set(candidate.universe.event_history), tuple(encounter.pending_action_list),
                  tuple(encounter._choice_book._choices), tuple(encounter._choice_book._drafts),
                  encounter.progression_mode, random.getstate())
        # r65 supplies Awareness, but the browser still exposes no target-free
        # Spot operation. Awareness alone does not start this Encounter.
        self.assertEqual(encounter.aware_beings(actor_id), [target_id])
        self.assertFalse(session.public_view()["spot_available"])
        self.assertFalse(encounter.initiated)
        action = SpotAction(candidate.universe, actor_id, target_id, start_time=0)
        with self.assertRaisesRegex(ValueError, "first Arena Choice"):
            encounter.activate_arena_for_player_action(actor_id, action,
                rng_owner=RNGCursor(random.Random(5302).getstate()))
        after = (encounter.time, encounter.last_processed_boundary, encounter.initiated,
                 encounter.initiation, dict(encounter.awareness),
                 set(candidate.universe.event_history), tuple(encounter.pending_action_list),
                 tuple(encounter._choice_book._choices), tuple(encounter._choice_book._drafts),
                 encounter.progression_mode, random.getstate())
        self.assertEqual(after, before)
        self.assertIsNone(candidate.universe.get_event_by_id(action.id))
        view = json.dumps(session.public_view())
        self.assertNotIn(target_id, view)
        self.assertNotIn(hidden.native.being.name, view)

    def test_explicit_test_geometry_proves_native_success_and_failure_at_boundary_six(self):
        for dc, expected in ((1, "success"), (100, "failure")):
            with self.subTest(dc=dc):
                candidate, encounter, player, hidden, ledger, prior_xp, record, intent = run_case(dc)
                self.assertEqual(encounter.start_time, 0)
                self.assertEqual(encounter.time, 6)
                self.assertEqual(record.resolved_boundary, 6)
                self.assertEqual(record.facts.outcome, expected)
                self.assertEqual(player.skill_experience, prior_xp)
                self.assertEqual(player.skill_experience.get("spot", 0), 0)
                self.assertNotIn("target_id", vars(intent))
                self.assertNotIn("action_id", vars(intent))
                self.assertNotIn(hidden.id, repr(intent))
                self.assertEqual(encounter.aware_beings(hidden.id), [])
                if expected == "success":
                    self.assertEqual(encounter.aware_beings(player.id), [hidden.id])
                    seen = ledger.last_seen_location(hidden.id)
                    self.assertEqual((seen.boundary, seen.observed_at), (6, 6))
                    self.assertEqual(seen.position, hidden.get_position())
                else:
                    self.assertEqual(encounter.aware_beings(player.id), [])
                    self.assertIsNone(ledger.last_seen_location(hidden.id))


if __name__ == "__main__":
    unittest.main()
