"""Reproduce native Spot with explicit test-only geometry and DCs.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_spot_geometry.py

The temporary Sphere and target DC values below are isolated test premises,
not production race geometry or generalized visibility rules. Each fixture
Encounter is explicitly constructed as already initiated; this does not prove
that an ordinary generated Arena can legally initiate from an unknown-target
player Action.
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_initialization import initialize_two_being_arena
from attention_intent import accept_spot_attention
from atomic_publication import RNGCursor
from encounter import Encounter
from location_observation import LocationEvidenceLedger
from spatial.geometry import Sphere
from universe import Universe
from being import BeingInstance


def run_case(discovery_dc):
    candidate = initialize_two_being_arena(0, 5, 5, root_seed=20261107)
    generated_player, generated_hidden = candidate.participants
    # Use the generated native definitions in a new world so the inactive
    # 004F Encounter's ChoiceBook is not a second owner of these same Beings.
    world = Universe("isolated test-only Spot geometry", library=candidate.universe.library)
    player = BeingInstance(generated_player.native.being.original.copy(),
                           name=generated_player.native.being.name)
    hidden = BeingInstance(generated_hidden.native.being.original.copy(),
                           name=generated_hidden.native.being.name)
    world.add_object(player)
    world.add_object(hidden)
    player.set_position(generated_player.native.being.get_position())
    hidden.set_position(generated_hidden.native.being.get_position())
    # Test-only shape premise: a 0.25 m Sphere centered at each explicitly
    # authored native position. This does not infer anatomy from race, height,
    # mass, map cells, or BeingDefinition dimensions.
    player.set_geometry(Sphere(0.25))
    hidden.set_geometry(Sphere(0.25))
    hidden.current.discovery_dc = discovery_dc

    encounter = Encounter(world, 15, 0, name="test-only initiated Encounter",
                          initiated=True, awareness={})
    world.add_event(encounter)
    encounter.add_being(player.id)
    encounter.add_being(hidden.id)
    cursor = RNGCursor(random.Random(5302).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=cursor)
    ledger = LocationEvidenceLedger(player.id)
    before_spot_xp = dict(player.skill_experience)
    intent = accept_spot_attention(
        encounter, player.id, location_ledger=ledger)
    assert intent.accepted and "target_id" not in vars(intent) and "action_id" not in vars(intent)

    for second in range(1, 7):
        encounter.step(1)
        assert encounter.time == second
        if second < 6:
            assert encounter.aware_beings(player.id) == []
            assert ledger.observations == ()

    record = encounter.inspect_committed(6).action(
        next(member.action.id
             for choice in encounter._choice_book._choices.values()
             for member in choice.members))
    return candidate, encounter, player, hidden, ledger, before_spot_xp, record, intent


def main():
    for discovery_dc, expected in ((1, "success"), (100, "failure")):
        candidate, encounter, player, hidden, ledger, prior_xp, record, intent = run_case(discovery_dc)
        assert "target_id" not in vars(intent) and "action_id" not in vars(intent)
        assert record.facts.outcome == expected
        assert player.skill_experience == prior_xp
        assert player.skill_experience.get("spot", 0) == 0
        if expected == "success":
            assert encounter.aware_beings(player.id) == [hidden.id]
            observation = ledger.last_seen_location(hidden.id)
            assert observation is not None and observation.boundary == 6 and observation.observed_at == 6
            assert observation.position == hidden.get_position()
        else:
            assert encounter.aware_beings(player.id) == []
            assert ledger.observations == ()
        print(f"test-only DC {discovery_dc}: {expected}; native t={encounter.time}; "
              f"resolved_boundary={record.resolved_boundary}; "
              f"player_awareness={len(encounter.aware_beings(player.id))}; "
              f"location_evidence={len(ledger.observations)}")
    print("Limit: explicit test geometry and an already-initiated test Encounter only; "
          "no production geometry or Arena initiation rule is implied.")


if __name__ == "__main__":
    main()
