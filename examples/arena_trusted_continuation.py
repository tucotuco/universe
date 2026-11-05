"""Two-process trusted-local continuation of the fixed native Arena.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 python3 examples/arena_trusted_continuation.py

Process A commits the six-second Spot and captures the existing B1/B2 data
representations, then completes an uninterrupted native Run boundary 7.
Process B independently admits that exact pair through B1/B2/B3 host approvals,
accepts it as local initial conditions, and publishes a new native Run at 7.
Imported boundaries remain labeled claims; they are never native receipts.
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

from activities import RunAction
from arena_history_prefix import capture_arena_history_prefix
from arena_state_candidate import capture_arena_post_spot_state
from examples.npc_encounter_arena import build_arena


ARI = "arena/being/ari"
BEX = "arena/being/bex"
RUN_ID = "npc-arena/action/run-ari-boundary-7"
HOST_RNG_SEED = 90210


def _signature(world, encounter, *, native_boundaries):
    view = encounter.inspect_committed(7)
    action = view.action(RUN_ID)
    target = view.target(ARI)
    practice = tuple({
        "being_id": use.being_id,
        "skill": use.skill_name,
        "experience": use.experience,
        "level_before": use.level_before,
        "level_after": use.level_after,
        "time": use.time,
        "causal_action_ids": tuple(row.action_id for row in use.exercises),
    } for use in target.practice_history)
    return {
        "encounter_id": view.encounter_id,
        "boundary": view.boundary,
        "action_id": action.declaration.id,
        "actor_id": action.declaration.actor_id,
        "target_id": action.declaration.target_id,
        "choice_id": action.lifecycle.choice_id,
        "outcome": action.facts.outcome,
        "metadata": tuple(action.facts.metadata),
        "effects": tuple((row.identity.encounter_id, row.identity.boundary,
                          row.identity.source_action_id, row.identity.channel,
                          row.identity.slot, type(row.effect).__name__)
                         for row in action.effects),
        "ari_position": tuple(world.get_object_by_id(ARI).get_position().as_tuple()),
        "bex_position": tuple(world.get_object_by_id(BEX).get_position().as_tuple()),
        "ari_hp": world.get_object_by_id(ARI).get_hit_points(),
        "bex_hp": world.get_object_by_id(BEX).get_hit_points(),
        "ari_awareness": tuple(sorted(encounter.awareness[ARI])),
        "bex_awareness": tuple(sorted(encounter.awareness[BEX])),
        "ari_practice": practice,
        "native_receipt_boundaries": tuple(row.boundary for row in encounter._atomic_interval_history),
        "native_receipt_count": len(encounter._atomic_interval_history),
        "native_inspection_boundaries": tuple(row.boundary for row in view.timeline),
    }


def _run_new_boundary(world, encounter, rng):
    action = RunAction(world, ARI, 6, 1, 0.5, experience=4, id=RUN_ID)
    encounter.schedule_choice((action,))
    encounter.step(1, velocities={ARI: (1, 0, 0), BEX: (0, 0, 0)})
    return _signature(world, encounter, native_boundaries=tuple(
        row.boundary for row in encounter._atomic_interval_history))


_CHILD = r'''
import base64, hashlib, json, random, sys
from arena_history_admission import (ExpectedArenaBinding, ExpectedArenaScenario,
    _host_authorize_arena_history, _prepare_arena_history_view)
from arena_history_prefix import decode_arena_history_prefix
from arena_state_candidate import decode_arena_post_spot_state
from arena_state_admission import (ExpectedArenaSource, _host_authorize_arena_state,
    _prepare_arena_state)
from arena_state_activation import (_activate_local_arena,
    _compose_committed_inspection, _host_authorize_local_activation)
from activities import RunAction
from atomic_publication import RNGCursor, _COMMITTED_RECEIPTS

envelope=json.loads(sys.stdin.buffer.read().decode('utf-8'))
prefix=decode_arena_history_prefix(base64.b64decode(envelope['history_prefix'],validate=True))
candidate=decode_arena_post_spot_state(base64.b64decode(envelope['state_candidate'],validate=True))
sources={key:base64.b64decode(value,validate=True) for key,value in envelope['sources'].items()}
scenario=ExpectedArenaScenario('0','npc-arena/encounter/1',
 'npc-arena/action/spot-ari-bex','arena/being/ari','arena/being/bex','0x0.0p+0',6)
bindings=tuple(ExpectedArenaBinding(row['binding_key'],row['source_sha256'],
 row['display_name'],row['native_being_id'],row['native_definition_name'],tuple(row['position']))
 for row in prefix.payload()['npc_bindings'])
history_cap=_host_authorize_arena_history(prefix,
 expected_content_sha256=prefix.content_sha256,expected_scenario=scenario,
 expected_bindings=bindings)
history=_prepare_arena_history_view(prefix,history_cap)
expected_sources=tuple(ExpectedArenaSource(key,sources[key]) for key in ('arena-ari','arena-bex'))
for row in expected_sources:
 assert hashlib.sha256(row.source_bytes).hexdigest()==next(x.source_sha256 for x in bindings if x.binding_key==row.binding_key)
state_cap=_host_authorize_arena_state(candidate,prefix,history,
 expected_content_sha256=candidate.content_sha256,expected_scenario=scenario,
 expected_bindings=bindings,expected_sources=expected_sources)
admitted=_prepare_arena_state(candidate,prefix,history,state_cap,
 expected_content_sha256=candidate.content_sha256,expected_scenario=scenario,
 expected_bindings=bindings,expected_sources=expected_sources)
prefix_before=prefix.to_bytes();candidate_before=candidate.to_bytes()
assert len(_COMMITTED_RECEIPTS)==0
active=_activate_local_arena(admitted,
 _host_authorize_local_activation(admitted,rng_seed=90210))
enc,world,rng=active.encounter,active.world,active.rng
fresh_rng_before=rng.state
assert enc.start_time==enc.time==6 and enc.last_processed_boundary==6
assert enc.__dict__.get('_atomic_interval_history',[])==[] and len(_COMMITTED_RECEIPTS)==0
action=RunAction(world,'arena/being/ari',6,1,0.5,experience=4,
 id='npc-arena/action/run-ari-boundary-7')
choice=enc.schedule_choice((action,))
enc.step(1,velocities={'arena/being/ari':(1,0,0),'arena/being/bex':(0,0,0)})
native=enc.inspect_committed(7)
composed=_compose_committed_inspection(active)
result_action=native.action(action.id);target=native.target('arena/being/ari')
practice=tuple({'being_id':u.being_id,'skill':u.skill_name,'experience':u.experience,
 'level_before':u.level_before,'level_after':u.level_after,'time':u.time,
 'causal_action_ids':tuple(x.action_id for x in u.exercises)} for u in target.practice_history)
effects=tuple((x.identity.encounter_id,x.identity.boundary,x.identity.source_action_id,
 x.identity.channel,x.identity.slot,type(x.effect).__name__) for x in result_action.effects)
assert rng.state==fresh_rng_before
assert tuple(row.boundary for row in composed.timeline)==tuple(range(1,8))
assert len(enc._atomic_interval_history)==1 and enc._atomic_interval_history[0].boundary==7
assert len(_COMMITTED_RECEIPTS)==1
assert tuple(row.boundary for row in native.timeline)==(7,)
assert prefix.to_bytes()==prefix_before and candidate.to_bytes()==candidate_before
assert {row.source_bytes for row in history.npc_bindings}==set(sources.values())
output={
 'encounter_id':native.encounter_id,'boundary':native.boundary,
 'action_id':result_action.declaration.id,'actor_id':result_action.declaration.actor_id,
 'target_id':result_action.declaration.target_id,'choice_id':result_action.lifecycle.choice_id,
 'outcome':result_action.facts.outcome,'metadata':tuple(result_action.facts.metadata),
 'effects':effects,'ari_position':world.get_object_by_id('arena/being/ari').get_position().as_tuple(),
 'bex_position':world.get_object_by_id('arena/being/bex').get_position().as_tuple(),
 'ari_hp':world.get_object_by_id('arena/being/ari').get_hit_points(),
 'bex_hp':world.get_object_by_id('arena/being/bex').get_hit_points(),
 'ari_awareness':tuple(sorted(enc.awareness['arena/being/ari'])),
 'bex_awareness':tuple(sorted(enc.awareness['arena/being/bex'])),
 'ari_practice':practice,'native_receipt_boundaries':(7,),
 'native_receipt_count':len(enc._atomic_interval_history),
 'native_inspection_boundaries':tuple(row.boundary for row in native.timeline),
 'composed_boundaries':tuple(row.boundary for row in composed.timeline),
 'composed_provenance':tuple(row.provenance for row in composed.timeline),
 'imported_trust':composed.imported_history.trust,
 'native_trust':'native/publisher-issued in this process',
 'source_provenance':active.source_provenance,
 'fresh_rng_unchanged':rng.state==fresh_rng_before,
 'choice_view_id':choice.id,
}
print(json.dumps(output,sort_keys=True,default=list))
'''


def _source_bytes():
    return {
        "arena-ari": (ROOT / "examples" / "npc_candidates" / "ari.npcgen.json").read_bytes(),
        "arena-bex": (ROOT / "examples" / "npc_candidates" / "bex.npcgen.json").read_bytes(),
    }


def run_demo():
    # Process A: source the exact admitted prefix/state and finish the ordinary
    # uninterrupted native Arena with the same boundary-7 Action declaration.
    baseline = build_arena(die_roll=20)
    prefix = capture_arena_history_prefix(baseline)
    candidate = capture_arena_post_spot_state(baseline, prefix)
    source_bytes = _source_bytes()
    baseline_signature = _run_new_boundary(
        baseline["encounter"].universe, baseline["encounter"], baseline["rng"])

    payload = {
        "history_prefix": base64.b64encode(prefix.to_bytes()).decode("ascii"),
        "state_candidate": base64.b64encode(candidate.to_bytes()).decode("ascii"),
        "sources": {key: base64.b64encode(value).decode("ascii")
                    for key, value in source_bytes.items()},
    }
    result = subprocess.run(
        [sys.executable, "-c", _CHILD], cwd=ROOT,
        input=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        capture_output=True, check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
             "PYTHONPATH": str(ROOT / "src") + ":" + str(ROOT)},
    )
    if result.returncode:
        raise RuntimeError("Process B failed: " + result.stderr.decode("utf-8", errors="replace"))
    resumed = json.loads(result.stdout.decode("utf-8"))
    expected = json.loads(json.dumps(baseline_signature, default=list))
    expected.update({
        "composed_boundaries": list(range(1, 8)),
        "composed_provenance": ["imported/host-accepted claim; original receipt authenticity not established"] * 6
                               + ["native/publisher-issued in this process"],
        "imported_trust": "host-accepted local historical claim; original native publisher receipts are not established",
        "native_trust": "native/publisher-issued in this process",
        "source_provenance": [[key, hashlib.sha256(source_bytes[key]).hexdigest(),
                                "arena/being/ari" if key == "arena-ari" else "arena/being/bex",
                                "Human", ["0x0.0p+0", "0x0.0p+0", "0x0.0p+0"]
                                if key == "arena-ari" else
                                ["0x1.8000000000000p+1", "0x0.0p+0", "0x0.0p+0"]]
                               for key in ("arena-ari", "arena-bex")],
        "fresh_rng_unchanged": True,
        "choice_view_id": "npc-arena/encounter/1/draft/2",
    })
    # A native receipt object is process-local and is not compared or serialized.
    # All supported causal and Target-owned interval results are compared.
    comparable = (
        "encounter_id", "boundary", "action_id", "actor_id", "target_id",
        "choice_id", "outcome", "metadata", "effects", "ari_position",
        "bex_position", "ari_hp", "bex_hp", "ari_awareness", "bex_awareness",
        "ari_practice", "composed_boundaries", "composed_provenance",
        "imported_trust", "native_trust", "source_provenance",
        "fresh_rng_unchanged", "choice_view_id",
    )
    for key in comparable:
        assert resumed.get(key) == expected.get(key), (
            f"Process B differs from uninterrupted Process A for {key}: "
            f"{resumed.get(key)!r} != {expected.get(key)!r}")
    assert resumed["native_receipt_boundaries"] == [7]
    assert resumed["native_receipt_count"] == 1
    assert resumed["native_inspection_boundaries"] == [7]
    print("Process A: uninterrupted native Arena committed Spot at boundary 6 and Run at boundary 7.")
    print("Process B: fresh process host-accepted the exact B1/B2 pair, reconstructed B3 native Beings, and issued a new native boundary-7 receipt.")
    print("Comparison: Action outcome/causality, movement, HP, Awareness, Target-owned Run practice, IDs, NPC source bytes and composed chronology match.")
    print("Provenance: imported boundaries 1-6 remain host-accepted claims; only boundary 7 is publisher-issued in Process B.")
    print("RNG: Process B used a new host-selected RNG cursor; Run consumed no draws. No imported RNG-authority or stochastic replay claim is made.")
    print(json.dumps(resumed, sort_keys=True, indent=2))
    return resumed


if __name__ == "__main__":
    run_demo()
