"""Two independently scheduled Arena controllers through native Encounter state."""
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "examples")]

from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from arena_web import make_handler


class TestArenaVsArena(unittest.TestCase):
    def create(self):
        session = GeneratedArenaSession()
        view = session.generate({
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "root_seed": "14", "equipment_mode": "equipped",
            "encounter_mode": "arena_vs_arena", "strategy_a": "attack_only",
            "strategy_b": "defense_only", "opponent_strategy": "none",
            "size_categories": {"player": None, "opponent": None},
        })
        return session, view

    def test_two_controllers_native_consequence_and_fresh_process_continuation(self):
        session, view = self.create()
        candidate = session.active_candidate
        self.assertEqual(view["arena_strategies"], ["attack_only", "defense_only"])
        self.assertFalse(view["manual_controls_available"])
        self.assertIsNotNone(view["spectator_projection"])
        start_hp = [row.native.being.get_hit_points() for row in candidate.participants]
        for _ in range(11):
            view = session.advance_one_second()
            json.dumps(view)
        actions = session._all_melee_actions(candidate)
        defenses = session._all_melee_defenses(candidate)
        self.assertTrue(any(row.actor_id == candidate.participants[0].native.being.id
                            for row in actions))
        self.assertTrue(any(row.actor_id == candidate.participants[1].native.being.id
                            for row in defenses))
        self.assertLess(candidate.participants[1].native.being.get_hit_points(), start_hp[1])
        saved = session.save_encounter_bytes()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "arena.json"
            checkpoint.write_bytes(saved)
            code = """import json,sys; from pathlib import Path; from arena_browser_session import GeneratedArenaSession; s=GeneratedArenaSession(); v=s.load_encounter_bytes(Path(sys.argv[1]).read_bytes()); assert v['encounter_mode']=='arena_vs_arena' and v['arena_strategies']==['attack_only','defense_only']; [s.advance_one_second() for _ in range(3)]; c=s.active_candidate; print(json.dumps({'time':c.encounter.time,'strategies':s._arena_strategies,'hp':[p.native.being.get_hit_points() for p in c.participants],'actions':[(a.actor_id,a.start_time,a.end_time) for a in s._all_melee_actions(c)],'defenses':[(a.actor_id,a.start_time,a.end_time) for a in s._all_melee_defenses(c)]},sort_keys=True))"""
            environment = dict(os.environ, PYTHONPATH=os.pathsep.join(
                (str(ROOT / "src"), str(ROOT / "examples"))))
            child = subprocess.run([sys.executable, "-B", "-c", code, str(checkpoint)],
                                   cwd=ROOT, env=environment, text=True,
                                   capture_output=True, check=True)
            for _ in range(3):
                session.advance_one_second()
            c = session.active_candidate
            expected = {"time": c.encounter.time, "strategies": session._arena_strategies,
                        "hp": [p.native.being.get_hit_points() for p in c.participants],
                        "actions": [(a.actor_id, a.start_time, a.end_time)
                                    for a in session._all_melee_actions(c)],
                        "defenses": [(a.actor_id, a.start_time, a.end_time)
                                     for a in session._all_melee_defenses(c)]}
            self.assertEqual(json.loads(child.stdout), json.loads(json.dumps(expected)))

    def test_player_vs_arena_remains_default_and_server_rejects_manual_action_in_spectator_mode(self):
        session = GeneratedArenaSession()
        default_view = session.generate({
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "root_seed": "14", "equipment_mode": "equipped", "opponent_strategy": "none",
            "size_categories": {"player": None, "opponent": None},
        })
        self.assertEqual(default_view["encounter_mode"], "player_vs_arena")
        self.assertTrue(default_view["manual_controls_available"])
        view = session.generate({
            "starting_experience": "1000", "width_cells": "5", "height_cells": "5",
            "root_seed": "14", "equipment_mode": "equipped", "opponent_strategy": "none",
            "encounter_mode": "arena_vs_arena", "strategy_a": "attack_only",
            "strategy_b": "defense_only", "size_categories": {"player": None, "opponent": None},
        })
        self.assertFalse(view["manual_controls_available"])
        self.assertEqual(view["arena_strategies"], ["attack_only", "defense_only"])

    def test_spectator_http_rejects_manual_action_without_native_mutation(self):
        session, _ = self.create()
        candidate = session.active_candidate

        def post(path, payload):
            handler_type = make_handler(session)
            handler = object.__new__(handler_type)
            handler.path = path
            handler.server = type("FakeServer", (), {"server_port": 8000})()
            handler.wfile = io.BytesIO()
            body = json.dumps(payload).encode("utf-8")
            handler.headers = {"Content-Length": str(len(body)),
                               "Content-Type": "application/json"}
            handler.rfile = io.BytesIO(body)
            response = {}
            handler._send = lambda status, body, content_type="application/json; charset=utf-8": response.update(
                status=status, body=body, content_type=content_type)
            handler.do_POST()
            return response

        before = (candidate.encounter.time, list(candidate.encounter.pending_action_list),
                  candidate.encounter.choice_state, session._rng_cursor.state)
        self.assertEqual(post("/api/generated/run", {})["status"], 409)
        self.assertEqual(post("/api/generated/melee-strike", {})["status"], 409)
        after = (candidate.encounter.time, list(candidate.encounter.pending_action_list),
                 candidate.encounter.choice_state, session._rng_cursor.state)
        self.assertEqual(after, before)

    def test_invalid_independent_strategy_pair_preserves_active_session(self):
        session, _ = self.create()
        old_candidate = session.active_candidate
        with self.assertRaises(ArenaBrowserRequestError):
            session.generate({"starting_experience":"1000", "width_cells":"5", "height_cells":"5",
                "encounter_mode":"arena_vs_arena", "strategy_a":"none", "strategy_b":"unknown",
                "size_categories":{"player":None,"opponent":None}})
        self.assertIs(session.active_candidate, old_candidate)
        self.assertEqual(session._arena_strategies, ["attack_only", "defense_only"])


if __name__ == "__main__":
    unittest.main()
