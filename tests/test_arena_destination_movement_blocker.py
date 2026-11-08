"""Regression for the boundary between explicit movement intent and unsupported geometry."""

import inspect
import json
import random
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from activities import RunAction
from arena_browser_session import GeneratedArenaSession
from arena_initialization import initialize_two_being_arena
from atomic_publication import RNGCursor
from spatial.state import SpatialState
from arena_web import make_handler
import io


class TestArenaDestinationMovementBlocker(unittest.TestCase):
    def test_spatial_state_remains_position_only_and_intent_requires_explicit_limits(self):
        candidate = initialize_two_being_arena(0, 5, 5, 20261107)
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        self.assertEqual(SpatialState.__annotations__, {"position": "CartesianPosition"})
        self.assertIn("velocities", inspect.signature(encounter.step).parameters)
        self.assertNotIn("destination", inspect.signature(encounter.step).parameters)
        self.assertIn("movement_intent", inspect.signature(encounter.step).parameters)
        self.assertIn("movement_conditions", inspect.signature(encounter.step).parameters)
        self.assertIsNone(encounter.choose_movement())
        self.assertEqual(player.sprint(), 0)
        self.assertNotIn("Run", player.current.skills.skills)

        start = player.get_position()
        action = RunAction(candidate.universe, player.id, 0, 1, 0.1, experience=0)
        encounter.activate_arena_for_player_action(
            player.id, action,
            rng_owner=RNGCursor(random.Random(candidate.root_seed).getstate()))
        encounter.step(1)
        result = encounter.inspect_committed(1).action(action.id)
        self.assertEqual(encounter.time, 1)
        self.assertEqual(result.facts.outcome, "no_movement")
        self.assertEqual(player.get_position(), start)
        self.assertEqual(encounter.aware_beings(player.id), [])

    def test_generated_browser_has_no_destination_route_or_partial_mutation(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        handler_type = make_handler(session)
        handler = object.__new__(handler_type)
        handler.path = "/api/generated/destination"
        handler.wfile = io.BytesIO()
        handler.rfile = io.BytesIO(json.dumps({"column": "4", "row": "4"}).encode())
        handler.headers = {"Content-Length": str(handler.rfile.getbuffer().nbytes)}
        response = {}
        handler._send = lambda status, body, content_type="application/json; charset=utf-8": response.update(
            status=status, body=body, content_type=content_type)
        handler.do_POST()
        self.assertEqual(response["status"], 404)
        self.assertEqual(session.active_candidate, None)
        self.assertEqual(session.public_view()["state"], "empty")


if __name__ == "__main__":
    unittest.main()
