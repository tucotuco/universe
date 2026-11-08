"""Reproduce target-free Arena activation followed by native Run at t=1."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from activities import RunAction
from arena_initialization import initialize_two_being_arena
from atomic_publication import RNGCursor


def main() -> None:
    candidate = initialize_two_being_arena(0, 5, 5, 20261107)
    encounter = candidate.encounter
    actor = candidate.participants[0].native.being
    start = actor.get_position()
    action = RunAction(candidate.universe, actor.id, 0, 1, 0.1, experience=0)

    choice, activation = encounter.activate_arena_for_player_action(
        actor.id, action,
        rng_owner=RNGCursor(random.Random(candidate.root_seed).getstate()))
    assert encounter.time == 0 and choice.state == "executing"
    assert encounter.initiated and encounter.initiation is None
    assert encounter.aware_beings(actor.id) == []
    assert not hasattr(activation, "target_id")

    encounter.step(1)
    result = encounter.inspect_committed(1).action(action.id)
    assert result.facts.outcome == "no_movement"
    assert actor.get_position() == start
    print({"choice": choice.state, "activation": activation.to_dict(),
           "time_seconds": encounter.time, "run_outcome": result.facts.outcome,
           "player_position_meters": start.as_tuple(), "movement": "none"})


if __name__ == "__main__":
    main()
