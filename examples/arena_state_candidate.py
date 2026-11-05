"""Fresh-process validation of the bounded detached Arena state candidate.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 python examples/arena_state_candidate.py

Process A commits the actual native Spot and exports the 003A history prefix
plus the 003B2 post-Spot state candidate. Process B authorizes only the known
history prefix through the existing 003B1 host policy, then checks candidate
consistency. That history approval does not authenticate the state candidate.
"""
from pathlib import Path
import base64
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from arena_history_prefix import capture_arena_history_prefix
from arena_state_candidate import capture_arena_post_spot_state
from examples.npc_encounter_arena import build_arena


_CHILD = r'''
import base64, json, sys
from arena_history_prefix import decode_arena_history_prefix
from arena_history_admission import (ExpectedArenaBinding, ExpectedArenaScenario,
    _host_authorize_arena_history, _prepare_arena_history_view)
from arena_state_candidate import decode_arena_post_spot_state, validate_arena_post_spot_state

envelope=json.loads(sys.stdin.buffer.read().decode('utf-8'))
prefix=decode_arena_history_prefix(base64.b64decode(envelope['history_prefix'],validate=True))
candidate=decode_arena_post_spot_state(base64.b64decode(envelope['state_candidate'],validate=True))
scenario=ExpectedArenaScenario('0','npc-arena/encounter/1',
    'npc-arena/action/spot-ari-bex','arena/being/ari','arena/being/bex','0x0.0p+0',6)
bindings=(
 ExpectedArenaBinding('arena-ari','fbbee87dab9b7047b13ee11bb4ad37385779381f60d1dfc3c230afc5251befde',
    'Ari','arena/being/ari','Human',('0x0.0p+0','0x0.0p+0','0x0.0p+0')),
 ExpectedArenaBinding('arena-bex','9da574a288bd4f62832324e30c38426c9e666988628e2989c713db28c8007570',
    'Bex','arena/being/bex','Human',('0x1.8000000000000p+1','0x0.0p+0','0x0.0p+0')))
token=_host_authorize_arena_history(prefix,expected_content_sha256=prefix.content_sha256,
    expected_scenario=scenario,expected_bindings=bindings)
history=_prepare_arena_history_view(prefix,token)
view=validate_arena_post_spot_state(candidate,prefix,history)
assert 'encounter' not in sys.modules
assert 'atomic_publication' not in sys.modules
assert 'checkpoint_restore_preparation' not in sys.modules
assert 'checkpoint_inventory' not in sys.modules
print(json.dumps({
 'candidate_schema':view.schema,
 'candidate_trust':view.trust,
 'history_prefix_sha256':view.history_prefix_sha256,
 'universe_id':view.universe_id,
 'universe_name':view.universe_name,
 'library_id':view.library_id,
 'encounter_id':view.encounter_id,
 'start_time':view.start_time,
 'time':view.time,
 'committed_boundary':view.committed_boundary,
 'participants':[{
    'id':row.being_id,'name':row.name,'native_type':row.native_type,
    'definition':row.definition_name,'definition_graph_sha256':row.definition_graph_sha256,
    'position':[float.fromhex(value) for value in row.position_hex],
    'geometry':{'kind':row.geometry[0],'radius':float.fromhex(row.geometry[1])},
    'hit_points':row.hit_points,'aware_of':list(row.aware_of),
    'target_history_boundaries':list(row.target_history_boundaries)}
   for row in view.participants],
 'rng_role':view.rng_role,'rng_scope':view.rng_scope,
 'authorization_boundary':'003B1 host approval applies only to the exact history prefix, not to this state candidate',
 'continuation':view.continuation,
},sort_keys=True,indent=2))
'''


def run_demo():
    # Process A: the fixture itself uses real native Encounter progression and
    # publisher commitment; capture reads its committed state without replay.
    scenario = build_arena(die_roll=20)
    prefix = capture_arena_history_prefix(scenario)
    candidate = capture_arena_post_spot_state(scenario, prefix)
    input_data = {
        "history_prefix": base64.b64encode(prefix.to_bytes()).decode("ascii"),
        "state_candidate": base64.b64encode(candidate.to_bytes()).decode("ascii"),
    }
    result = subprocess.run(
        [sys.executable, "-c", _CHILD], cwd=ROOT,
        input=json.dumps(input_data, separators=(",", ":")).encode("utf-8"),
        check=True, capture_output=True,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1",
             "PYTHONPATH": str(ROOT / "src") + ":" + str(ROOT)},
    )
    print("Process A committed actual native Ari→Bex Spot at boundary 6.")
    print("Process B decoded and checked the detached prefix and state candidate.")
    print("The state candidate is an untrusted claim; B1 approval did not authorize its new fields.")
    output = result.stdout.decode("utf-8")
    print(output.rstrip())
    return output


if __name__ == "__main__":
    run_demo()
