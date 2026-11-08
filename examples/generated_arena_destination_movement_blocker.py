"""Reproduce the current generated-Arena destination-movement blocker."""

from __future__ import annotations

import inspect
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from activities import RunAction
from arena_initialization import initialize_two_being_arena
from atomic_publication import RNGCursor
from spatial.state import SpatialState


def main() -> None:
    candidate = initialize_two_being_arena(0, 5, 5, 20261107)
    encounter = candidate.encounter
    player = candidate.participants[0].native.being
    start = player.get_position()
    movement_choice_result = encounter.choose_movement()
    action = RunAction(candidate.universe, player.id, 0, 1, 0.1, experience=0)
    choice, activation = encounter.activate_arena_for_player_action(
        player.id, action,
        rng_owner=RNGCursor(random.Random(candidate.root_seed).getstate()))
    encounter.step(1)
    outcome = encounter.inspect_committed(1).action(action.id).facts.outcome

    evidence = {
        "choice_state": choice.state,
        "activation_kind": activation.activation_kind,
        "time_seconds": encounter.time,
        "run_outcome": outcome,
        "position_unchanged": player.get_position() == start,
        "native_sprint_value": player.sprint(),
        "generated_skill_names": sorted(player.current.skills.skills),
        "spatial_state_fields": sorted(SpatialState.__annotations__),
        "step_parameters": list(inspect.signature(encounter.step).parameters),
        "destination_api_available": "destination" in inspect.signature(encounter.step).parameters,
        "choose_movement_result": movement_choice_result,
    }
    assert outcome == "no_movement" and evidence["position_unchanged"]
    assert evidence["native_sprint_value"] == 0
    assert evidence["spatial_state_fields"] == ["position"]
    assert evidence["destination_api_available"] is False
    print(evidence)


if __name__ == "__main__":
    main()
