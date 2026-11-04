"""Run the first two-candidate, native Universe Encounter Arena.

From the repository root:
    python examples/npc_encounter_arena.py

This is a developer-facing scenario report. NPC Generator records are retained
as provenance; except for display names, the native Being definition, geometry,
positions, Action, and Spot roll are authored by this Arena fixture.
"""

from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import SpotAction
from atomic_publication import RNGCursor
from arena_npc_import import ArenaBindingBook, NPCandidate
from encounter import Encounter
from library import Library
from spatial import CartesianPosition, Sphere
from universe import Universe


def build_arena(*, die_roll=20, resolve=True):
    """Build and resolve one fresh deterministic two-Being Arena."""
    world = Universe(
        "NPC candidate Arena",
        library=Library(config_dir=str(ROOT / "src" / "config")),
    )
    binding_book = ArenaBindingBook(world)
    candidates = {
        name: NPCandidate.from_file(ROOT / "examples" / "npc_candidates" / f"{name}.npcgen.json")
        for name in ("ari", "bex")
    }
    ari = binding_book.bind(
        candidates["ari"], binding_key="arena-ari",
        native_being_id="arena/being/ari", native_definition_name="Human",
        position=CartesianPosition(0, 0, 0), geometry=Sphere(0.5),
    )
    bex = binding_book.bind(
        candidates["bex"], binding_key="arena-bex",
        native_being_id="arena/being/bex", native_definition_name="Human",
        position=CartesianPosition(3, 0, 0), geometry=Sphere(0.5),
    )

    encounter = Encounter(
        world, difficulty_class=15, start_time=0, initiated=True,
        id="npc-arena/encounter/1",
        awareness={ari.native_being_id: (), bex.native_being_id: ()},
    )
    world.add_event(encounter)
    encounter.add_being(ari.native_being_id)
    encounter.add_being(bex.native_being_id)
    rng = RNGCursor(random.Random(74001).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)

    spot = SpotAction(
        world, ari.native_being_id, bex.native_being_id, start_time=0,
        duration=6, die_roll=die_roll, id="npc-arena/action/spot-ari-bex",
    )
    encounter.schedule_choice((spot,))
    rng_before = rng.state
    view = None
    action = None
    committed_boundaries = ()
    if resolve:
        encounter.step(6)
        view = encounter.inspect_committed(6)
        action = view.action(spot.id)
        committed_boundaries = tuple(row.boundary for row in encounter._atomic_interval_history)
    summary = {
        "candidate_bindings": (ari, bex),
        "candidates": candidates,
        "being_positions": {
            ari.native_being_id: world.get_object_by_id(ari.native_being_id).get_position().as_tuple(),
            bex.native_being_id: world.get_object_by_id(bex.native_being_id).get_position().as_tuple(),
        },
        "encounter": encounter,
        "action": action,
        "spot_action": spot,
        "rng": rng,
        "rng_unchanged": rng.state == rng_before,
        "spot_awareness": {
            ari.native_being_id: tuple(encounter.aware_beings(ari.native_being_id)),
            bex.native_being_id: tuple(encounter.aware_beings(bex.native_being_id)),
        },
        "committed_boundary_count": len(encounter.__dict__.get("_atomic_interval_history", ())),
        "committed_boundaries": committed_boundaries,
    }
    return summary


def format_arena(summary):
    ari, bex = summary["candidate_bindings"]
    action = summary["action"]
    lines = [
        "UNIVERSE ENCOUNTER ARENA — developer inspection",
        "NPC Generator data is source provenance, not active Universe mechanics.",
        "Native defaults: Universe Human definition; Arena-authored geometry and Cartesian positions.",
        "Coordinates: Arena-authored Universe spatial units; no NPC size or external grid conversion.",
        "",
        "Participants",
    ]
    for binding in (ari, bex):
        candidate = summary["candidates"]["ari" if binding is ari else "bex"]
        source_state = candidate.source_record_copy()["state"]
        source_record = candidate.source_record_copy()
        pos = summary["being_positions"][binding.native_being_id]
        lines.append(
            f"  {binding.display_name}: native_id={binding.native_being_id}; "
            f"position={pos}; native_definition={binding.native_definition_name}; "
            f"source_seed={candidate.generation_seed}; source_engine={candidate.engine_version}; "
            f"source_rules={candidate.rules_hash}; source_sha256={candidate.content_sha256}; "
            f"source_edits={len(source_record['edits'])}; source_race_index={source_state['race']}; "
            f"source_hp={source_state['hps']} (metadata only)"
        )
    lines += [
        "",
        "Property boundary",
        "  NPC name -> display name only.",
        "  NPC race, scores, class/level/XP, HP, psionics, possessions, dimensions, and family -> preserved source data only.",
        "  NPC Generator has no discrete Universe skill list; no imported skill or equipment mechanics are active.",
        "",
        "Committed Encounter timeline",
        f"  t=0: native Spot accepted; Action={action.declaration.id}; duration=6 seconds.",
        f"  t=6: outcome={action.facts.outcome}; roll/DC="
        f"{dict(action.facts.metadata).get('roll')}/{dict(action.facts.metadata).get('effective_dc')}; "
        f"committed boundaries={summary['committed_boundaries']}.",
        f"  observer Awareness: Ari={summary['spot_awareness'][ari.native_being_id]}; "
        f"Bex={summary['spot_awareness'][bex.native_being_id]}.",
        f"  fixed Arena-authored d20 roll; authoritative RNG unchanged={summary['rng_unchanged']}.",
        "  This is developer inspection; the target identity was scenario-authored for this deliberate Spot.",
    ]
    return "\n".join(lines)


def main():
    print(format_arena(build_arena()))


if __name__ == "__main__":
    main()
