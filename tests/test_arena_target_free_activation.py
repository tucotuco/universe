"""Native approved target-free Arena activation transaction tests."""

import random
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from action_choice import ChoiceRejected
from activities import RunAction
from arena_initialization import initialize_two_being_arena
from atomic_publication import RNGCursor


class TestArenaTargetFreeActivation(unittest.TestCase):
    def setUp(self):
        self.candidate = initialize_two_being_arena(0, 5, 5, 20261107)
        self.encounter = self.candidate.encounter
        self.player = self.candidate.participants[0].native.being
        self.rng = RNGCursor(random.Random(self.candidate.root_seed).getstate())

    def action(self, *, id=None):
        return RunAction(self.candidate.universe, self.player.id, 0, 1, 0.1,
                         experience=0, id=id)

    def test_first_run_choice_activates_and_commits_native_second(self):
        start = self.player.get_position()
        action = self.action()
        choice, activation = self.encounter.activate_arena_for_player_action(
            self.player.id, action, rng_owner=self.rng)
        self.assertEqual(choice.state, "executing")
        self.assertEqual(activation.encounter_id, self.encounter.id)
        self.assertEqual(activation.actor_id, self.player.id)
        self.assertEqual(activation.time, 0)
        self.assertEqual(activation.activation_kind, "first_player_choice")
        self.assertFalse(hasattr(activation, "target_id"))
        self.assertTrue(self.encounter.initiated)
        self.assertIsNone(self.encounter.initiation)
        self.assertEqual(self.encounter.aware_beings(self.player.id), [])
        self.assertEqual(self.encounter.time, 0)

        self.encounter.step(1)
        result = self.encounter.inspect_committed(1).action(action.id)
        self.assertEqual(result.facts.outcome, "no_movement")
        self.assertEqual(self.encounter.time, 1)
        self.assertEqual(self.player.get_position(), start)

    def test_invalid_choice_restores_proposal_validation_and_publication_state(self):
        action = self.action(id=self.encounter.id)
        history = dict(self.candidate.universe.event_history)
        counter = self.encounter._choice_book._counter
        revision = self.encounter._choice_book.revision
        rng_state = self.rng.state
        with self.assertRaises(ChoiceRejected):
            self.encounter.activate_arena_for_player_action(
                self.player.id, action, rng_owner=self.rng)
        self.assertFalse(self.encounter.initiated)
        self.assertIsNone(self.encounter.arena_activation)
        self.assertEqual(self.encounter.time, 0)
        self.assertEqual(self.candidate.universe.event_history, history)
        self.assertEqual(self.encounter.pending_action_list, [])
        self.assertEqual(self.encounter._choice_book._counter, counter)
        self.assertEqual(self.encounter._choice_book._drafts, {})
        self.assertEqual(self.encounter._choice_book._tokens, {})
        self.assertEqual(self.encounter._choice_book._choices, {})
        self.assertEqual(self.encounter._choice_book.revision, revision)
        self.assertEqual(self.rng.state, rng_state)

    def test_failure_after_action_publication_rolls_back_whole_activation(self):
        action = self.action()
        history = dict(self.candidate.universe.event_history)
        revision = self.encounter._choice_book.revision
        rng_state = self.rng.state
        with patch("transactional_progression._enable_transactional_progression_owned",
                   side_effect=RuntimeError("injected activation abort")):
            with self.assertRaises(RuntimeError):
                self.encounter.activate_arena_for_player_action(
                    self.player.id, action, rng_owner=self.rng)
        self.assertFalse(self.encounter.initiated)
        self.assertIsNone(self.encounter.arena_activation)
        self.assertEqual(self.encounter.time, 0)
        self.assertEqual(self.candidate.universe.event_history, history)
        self.assertEqual(self.encounter.pending_action_list, [])
        self.assertEqual(self.encounter._choice_book._drafts, {})
        self.assertEqual(self.encounter._choice_book._tokens, {})
        self.assertEqual(self.encounter._choice_book._choices, {})
        self.assertEqual(self.encounter._choice_book._registered, {})
        self.assertEqual(self.encounter._choice_book.revision, revision)
        self.assertEqual(self.rng.state, rng_state)


if __name__ == "__main__":
    unittest.main()
