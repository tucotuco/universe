"""Run two bounded 5x5 time-zero Arena initialization proofs (0 and 12,000 XP)."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_initialization import ArenaInitializationRefusal, initialize_two_being_arena
from library import Library


def main():
    library = Library(config_dir=str(ROOT / "src/config"))
    for xp in (0, 12000):
        try:
            candidate = initialize_two_being_arena(xp, 5, 5, root_seed=20261107, library=library)
        except ArenaInitializationRefusal as exc:
            print(f"{xp} XP: {exc.code}: {exc.message}")
            continue
        print(f"{xp} XP: Encounter {candidate.encounter.id}, t={candidate.encounter.time}, "
              f"attempts={len(candidate.attempts)}, map=5x5 hexes (one yard across flats)")
        for participant in candidate.participants:
            print(f"  {participant.role}: native_id={participant.native.being.id}, "
                  f"source_sha256={participant.native.source_sha256}, "
              f"hex=({participant.placement.column},{participant.placement.row}), "
                  f"position_m={participant.placement.position}")
    print("Limits: two Beings only; no equipment, AI, observation layer, GUI, or generalized save; "
          "native race support remains limited to five exact names.")


if __name__ == "__main__":
    main()
