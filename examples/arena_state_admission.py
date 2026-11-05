"""Two-process host admission and quarantine-only native Arena inspection.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 python examples/arena_state_admission.py

Process A commits the real six-second Spot and exports B1/B2 candidates. The
fresh Process B independently selects the exact local NPC source bytes, admits
the history through B1, separately admits the state candidate, and constructs
private quarantined native BeingInstances. No Encounter or continuation is
constructed.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from arena_history_prefix import capture_arena_history_prefix
from arena_state_candidate import capture_arena_post_spot_state
from examples.npc_encounter_arena import build_arena


_CHILD = r'''
import base64, hashlib, json, sys
from arena_history_admission import (ExpectedArenaBinding, ExpectedArenaScenario,
    _host_authorize_arena_history, _prepare_arena_history_view)
from arena_history_prefix import decode_arena_history_prefix
from arena_state_candidate import decode_arena_post_spot_state
from arena_state_admission import (ExpectedArenaSource, _host_authorize_arena_state,
    _prepare_arena_state)

envelope=json.loads(sys.stdin.buffer.read().decode('utf-8'))
prefix=decode_arena_history_prefix(base64.b64decode(envelope['history_prefix'],validate=True))
candidate=decode_arena_post_spot_state(base64.b64decode(envelope['state_candidate'],validate=True))
source_bytes={key:base64.b64decode(value,validate=True)
    for key,value in envelope['host_source_bytes'].items()}
scenario=ExpectedArenaScenario('0','npc-arena/encounter/1',
    'npc-arena/action/spot-ari-bex','arena/being/ari','arena/being/bex','0x0.0p+0',6)
rows=prefix.payload()['npc_bindings']
bindings=tuple(ExpectedArenaBinding(row['binding_key'],row['source_sha256'],
    row['display_name'],row['native_being_id'],row['native_definition_name'],
    tuple(row['position'])) for row in rows)
history_cap=_host_authorize_arena_history(prefix,
    expected_content_sha256=prefix.content_sha256,expected_scenario=scenario,
    expected_bindings=bindings)
history=_prepare_arena_history_view(prefix,history_cap)
sources=tuple(ExpectedArenaSource(key,source_bytes[key])
    for key in ('arena-ari','arena-bex'))
for key,raw in source_bytes.items():
    assert hashlib.sha256(raw).hexdigest()==next(row.source_sha256 for row in bindings if row.binding_key==key)
state_cap=_host_authorize_arena_state(candidate,prefix,history,
    expected_content_sha256=candidate.content_sha256,expected_scenario=scenario,
    expected_bindings=bindings,expected_sources=sources)
admitted=_prepare_arena_state(candidate,prefix,history,state_cap,
    expected_content_sha256=candidate.content_sha256,expected_scenario=scenario,
    expected_bindings=bindings,expected_sources=sources)
assert 'encounter' not in sys.modules
assert 'atomic_publication' not in sys.modules
assert 'checkpoint_restore_preparation' not in sys.modules
assert not hasattr(admitted,'step') and not hasattr(admitted,'accept_choice')
view=admitted.view
assert view.candidate_state_view.time==6.0 and view.candidate_state_view.committed_boundary==6
assert view.history_view.observer_view('arena/being/ari').aware_of==('arena/being/bex',)
assert view.history_view.observer_view('arena/being/bex').aware_of==()
print(json.dumps({
 'schema':view.schema,'trust':view.trust,
 'candidate_sha256':view.candidate_sha256,
 'history_prefix_sha256':view.history_prefix_sha256,
 'time':view.time,'committed_boundary':view.committed_boundary,
 'sources':[{'binding_key':r[0],'sha256':r[1],'name':r[2],
    'being_id':r[3],'definition':r[4]} for r in view.source_provenance],
 'beings':[{'id':r.being_id,'name':r.name,'definition':r.definition_name,
    'hit_points':r.hit_points,'position_hex':r.position_hex,
    'geometry':{'kind':r.geometry_kind,'radius_hex':r.geometry_radius_hex},
    'quarantined':r.quarantined} for r in view.beings],
 'ari_aware_of':list(view.history_view.observer_view('arena/being/ari').aware_of),
 'bex_aware_of':list(view.history_view.observer_view('arena/being/bex').aware_of),
 'rng_role':view.rng_role,'rng_scope':view.rng_scope,
 'continuation':view.continuation,
},sort_keys=True,indent=2))
'''


def run_demo():
    # Process A: use the real native transactional Arena fixture.
    scenario = build_arena(die_roll=20)
    prefix = capture_arena_history_prefix(scenario)
    candidate = capture_arena_post_spot_state(scenario, prefix)
    source_bytes = {
        key: (ROOT / "examples" / "npc_candidates" / f"{key.split('-')[1]}.npcgen.json").read_bytes()
        for key in ("arena-ari", "arena-bex")
    }
    payload = {
        "history_prefix": base64.b64encode(prefix.to_bytes()).decode("ascii"),
        "state_candidate": base64.b64encode(candidate.to_bytes()).decode("ascii"),
        "host_source_bytes": {key: base64.b64encode(value).decode("ascii")
                              for key, value in source_bytes.items()},
    }
    result = subprocess.run(
        [sys.executable, "-c", _CHILD], cwd=ROOT,
        input=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        capture_output=True, check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
             "PYTHONPATH": str(ROOT / "src") + ":" + str(ROOT)},
    )
    reconstructed = json.loads(result.stdout.decode("utf-8"))
    state = candidate.view()
    expected_beings = [{
        "id": row.being_id, "name": row.name, "definition": row.definition_name,
        "hit_points": row.hit_points, "position_hex": list(row.position_hex),
        "geometry": {"kind": row.geometry[0], "radius_hex": row.geometry[1]},
        "quarantined": True,
    } for row in state.participants]
    expected_sources = [{
        "binding_key": row["binding_key"], "sha256": row["source_sha256"],
        "name": row["display_name"], "being_id": row["native_being_id"],
        "definition": row["native_definition_name"],
    } for row in prefix.payload()["npc_bindings"]]
    assert reconstructed["beings"] == expected_beings
    assert reconstructed["sources"] == expected_sources
    assert reconstructed["candidate_sha256"] == candidate.content_sha256
    assert reconstructed["history_prefix_sha256"] == prefix.content_sha256
    assert reconstructed["time"] == state.time == 6.0
    assert reconstructed["committed_boundary"] == state.committed_boundary == 6
    assert reconstructed["ari_aware_of"] == list(prefix.payload()["targets"][0]["aware_of"])
    assert reconstructed["bex_aware_of"] == list(prefix.payload()["targets"][1]["aware_of"])
    print("Process A committed native Ari→Bex Spot at boundary 6.")
    print("Process B admitted the exact B1 history and separately host-approved B2 state.")
    print("Process B reconstructed quarantined native BeingInstances; its public result is detached.")
    output = result.stdout.decode("utf-8")
    print(output.rstrip())
    return output


if __name__ == "__main__":
    run_demo()
