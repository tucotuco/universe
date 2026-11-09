"""Geometry and Encounter-initiation readiness proofs for generated Arena Spot."""

from pathlib import Path
import json
import random
import sys
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
from interval_staging import IntervalIntegrityError
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
                self.assertEqual(definition.body_parts, {})
                self.assertFalse(hasattr(definition, "geometry"))

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
        with self.assertRaisesRegex(IntervalIntegrityError, "initiated"):
            encounter.enable_transactional_progression(
                quiescent=True, rng_owner=RNGCursor(random.Random(5302).getstate()))
        action = SpotAction(candidate.universe, actor_id, target_id, start_time=0)
        with self.assertRaisesRegex(RuntimeError, "Encounter must be initiated"):
            encounter.schedule_action(action)
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
