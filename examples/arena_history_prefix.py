"""Demonstrate a fresh-process import of the Arena's detached Spot history.

Run from the repository root with:
    PYTHONDONTWRITEBYTECODE=1 python examples/arena_history_prefix.py

The imported value is historical data only. This does not restore or resume an
Encounter and does not authenticate the original publisher in the child.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_history_prefix import capture_arena_history_prefix
from npc_encounter_arena import build_arena


_CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from arena_history_prefix import decode_arena_history_prefix
assert 'atomic_publication' not in sys.modules
assert 'encounter' not in sys.modules
prefix = decode_arena_history_prefix(sys.stdin.buffer.read())
print(json.dumps(prefix.summary(), sort_keys=True, separators=(',', ':')))
'''


def main():
    scenario = build_arena(die_roll=20)
    encounter = scenario["encounter"]
    before = (encounter.time, tuple(encounter._atomic_interval_history),
              scenario["rng"].state,
              tuple(encounter.aware_beings(scenario["candidate_bindings"][0].native_being_id)),
              tuple(encounter.aware_beings(scenario["candidate_bindings"][1].native_being_id)))
    prefix = capture_arena_history_prefix(scenario)
    wire = prefix.to_bytes()
    after = (encounter.time, tuple(encounter._atomic_interval_history),
             scenario["rng"].state,
             tuple(encounter.aware_beings(scenario["candidate_bindings"][0].native_being_id)),
             tuple(encounter.aware_beings(scenario["candidate_bindings"][1].native_being_id)))
    if before != after:
        raise RuntimeError("detached export changed native Arena state")
    child = subprocess.run(
        [sys.executable, "-c", _CHILD, str(ROOT / "src")],
        input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=ROOT, check=False,
    )
    if child.returncode:
        raise RuntimeError(child.stderr.decode("utf-8", errors="replace"))
    print("Fresh-process detached Arena history (not a restored Encounter):")
    print(json.dumps(json.loads(child.stdout), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
