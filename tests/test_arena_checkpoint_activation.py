import unittest

from arena_browser_session import GeneratedArenaSession
from checkpoint_inventory import CheckpointRejected, capture_checkpoint_candidate


class GeneratedArenaCheckpointActivationTests(unittest.TestCase):
    def test_first_movement_boundary_remains_live_when_strict_checkpoint_refuses(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        opponent = candidate.participants[1].native.being
        start = player.get_position()

        origin = candidate.arena_map.layout.cell_at_position(start)
        destination = next(address for address in candidate.arena_map.layout.addresses()
                           if address != origin)
        session.choose_destination({"column": destination.column,
                                    "row": destination.row,
                                    "rate": "sprint",
                                    "facing_policy": "turn"})
        self.assertIsNotNone(session._movement_plan)
        session.advance_one_second()

        self.assertEqual((encounter.last_processed_boundary, encounter.time), (1, 1))
        self.assertNotEqual(player.get_position().as_tuple(), start.as_tuple())
        self.assertIsNotNone(encounter.arena_movement_activation)
        player_ledger = player._arena_perception_ledger
        opponent_ledger = opponent._arena_perception_ledger
        self.assertIn(opponent.id, tuple(row.entity_id for row in player_ledger.current))
        self.assertIn(player.id, tuple(row.entity_id for row in opponent_ledger.current))

        before = (encounter.time, player.get_position().as_tuple(),
                  session._movement_plan, session._rng_cursor.state,
                  tuple(player_ledger.history), tuple(opponent_ledger.history))
        with self.assertRaisesRegex(CheckpointRejected,
                                    "movement-activated Arena Encounter cannot be resumed"):
            capture_checkpoint_candidate(candidate.universe, encounter,
                quiescent=True, rng_scope="exclusive_encounter", native_adapters=True)
        after = (encounter.time, player.get_position().as_tuple(),
                 session._movement_plan, session._rng_cursor.state,
                 tuple(player_ledger.history), tuple(opponent_ledger.history))
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
