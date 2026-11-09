import unittest

from arena_browser_session import GeneratedArenaSession
from checkpoint_inventory import capture_checkpoint_candidate, validate_checkpoint_candidate


def _find_activation_node(value):
    if type(value) is tuple:
        if len(value) == 3 and value[1] == "encounter.ArenaMovementActivation":
            return value
        for child in value:
            found = _find_activation_node(child)
            if found is not None:
                return found
    return None


class GeneratedArenaCheckpointActivationTests(unittest.TestCase):
    def test_first_movement_boundary_closes_receipt_before_next_strict_checkpoint_refusal(self):
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

        book = encounter._choice_book
        before = (encounter.time, encounter.last_processed_boundary,
                  tuple((participant.native.being.id,
                         participant.native.being.get_position().as_tuple(),
                         participant.native.being.get_posture(),
                         participant.native.being.hex_facing)
                        for participant in candidate.participants),
                  encounter.initiated, encounter.arena_activation_enabled,
                  encounter.arena_activation, encounter.arena_movement_activation,
                  session._movement_plan, session._rng_cursor.state,
                  (book._counter, tuple(book._choices.items()), tuple(book._states.items()),
                   tuple(encounter.pending_action_list)),
                  tuple(player_ledger.history), tuple(opponent_ledger.history))
        captured = capture_checkpoint_candidate(candidate.universe, encounter,
            quiescent=True, rng_scope="exclusive_encounter", native_adapters=True)
        validation = validate_checkpoint_candidate(candidate.universe, encounter,
            captured, quiescent=True)
        self.assertTrue(validation.inventory_validated)
        self.assertFalse(captured.closure_validated)
        self.assertFalse(captured.portable_schema_defined)
        self.assertFalse(captured.restore_verified)
        self.assertIn("bounded_run_spot_closure_verified",
                      {row.code for row in captured.diagnostics})
        activation_node = _find_activation_node(captured.envelope)
        self.assertIsNotNone(activation_node)
        activation_fields = dict(activation_node[2])
        self.assertEqual(activation_fields["encounter_id"], ("string", encounter.id))
        self.assertEqual(activation_fields["actor_id"], ("string", player.id))
        self.assertEqual(activation_fields["movement_decision_id"],
                         ("string", encounter.arena_movement_activation.movement_decision_id))
        self.assertEqual(activation_fields["time"], ("integer", "0"))
        self.assertEqual(activation_fields["activation_kind"],
                         ("string", "first_player_movement"))
        after = (encounter.time, encounter.last_processed_boundary,
                 tuple((participant.native.being.id,
                        participant.native.being.get_position().as_tuple(),
                        participant.native.being.get_posture(),
                        participant.native.being.hex_facing)
                       for participant in candidate.participants),
                 encounter.initiated, encounter.arena_activation_enabled,
                 encounter.arena_activation, encounter.arena_movement_activation,
                 session._movement_plan, session._rng_cursor.state,
                 (book._counter, tuple(book._choices.items()), tuple(book._states.items()),
                  tuple(encounter.pending_action_list)),
                 tuple(player_ledger.history), tuple(opponent_ledger.history))
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
