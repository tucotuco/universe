"""Loopback-only presentation adapter for the bounded native Encounter Arena."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit
from activities import RunAction, SpotAction
from action_choice import ChoiceRejected
from arena_history_prefix import capture_arena_history_prefix
from arena_state_candidate import capture_arena_post_spot_state
from arena_local_checkpoint import (
    ArenaLocalCheckpointRejected,
    encode_local_bundle,
    write_local_bundle,
)
from arena_s7_checkpoint import capture_s7_candidate
from examples.npc_encounter_arena import build_unstarted_arena
from arena_state_activation import _compose_committed_inspection
from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
class ArenaRequestError(ValueError):
    """Request is outside the allowlisted Arena operations."""
class ArenaSession:
    """One in-memory native transactional Arena; Universe remains authoritative."""
    def __init__(self, *, die_roll=20, save_path=None, active=None):
        self.active = active
        self.save_path = save_path
        self._saved = False
        if active is None:
            self.scenario = build_unstarted_arena(die_roll=die_roll)
            self.encounter = self.scenario["encounter"]
            self.world = self.encounter.universe
            self.ari, self.bex = self.scenario["candidate_bindings"]
            self.rng = self.scenario["rng"]
        else:
            self.scenario = None
            self.encounter = active.encounter
            self.world = active.world
            self.rng = active.rng
            bindings = {row.native_being_id: row for row in active.imported_history.npc_bindings}
            self.ari = bindings["arena/being/ari"]
            self.bex = bindings["arena/being/bex"]
            self._base_bundle_wire = active.bundle_wire
        if active is None:
            self._base_bundle_wire = None
        self.die_roll = die_roll
        self._rng_initial = self.rng.state
        self._spot = None
        self._choice = None
        self._run = None
        self._run_choice = None
        self._lock = RLock()
    def _inspection(self):
        if self.encounter.time < 1 or (self.active is not None
                and self.encounter.time == self.active.start_boundary):
            return None
        return self.encounter.inspect_committed(int(self.encounter.time))
    def _position(self, being_id, inspection):
        position = (inspection.target(being_id).position if inspection is not None
                    else self.world.get_object_by_id(being_id).get_position())
        if position is None:
            return None
        x, y, _ = position.as_tuple()
        return {"x": x, "y": y}
    def gm_view(self):
        """Omniscient developer projection from native state and committed inspection."""
        with self._lock:
            inspection = self._inspection()
            participants = []
            for binding in (self.ari, self.bex):
                participants.append({
                    "name": binding.display_name,
                    "id": binding.native_being_id,
                    "position": self._position(binding.native_being_id, inspection),
                    "hit_points": self.world.get_object_by_id(binding.native_being_id).get_hit_points(),
                    "run_experience": self.world.get_object_by_id(binding.native_being_id).skill_experience.get("run", 0),
                    "aware_of": list(self.encounter.aware_beings(binding.native_being_id)),
                    "native_definition": binding.native_definition_name,
                    "source_sha256": binding.source_sha256,
                })
            choice = self.encounter.get_choice(self._run_choice.id) if self._run_choice is not None else (
                self.encounter.get_choice(self._choice.id) if self._choice is not None else None)
            committed_action = None
            if inspection is not None:
                action_id = (self._run.id if self._run is not None
                            else self._spot.id if self._spot is not None else None)
                if action_id is not None and action_id in inspection.actions:
                    result = inspection.action(action_id)
                    facts = dict(result.facts.metadata)
                    committed_action = {
                        "id": action_id, "boundary": result.resolved_boundary,
                        "actor_id": result.declaration.actor_id,
                        "target_id": result.declaration.target_id,
                        "choice_id": result.lifecycle.choice_id,
                        "outcome": result.facts.outcome, "roll": facts.get("roll"),
                        "effective_dc": facts.get("effective_dc"),
                        "metadata": facts,
                        "effect_ids": [str(effect.identity) for effect in result.effects],
                        "practice": [{
                            "being_id": row.being_id, "skill": row.skill_name,
                            "experience": row.experience, "time": row.time,
                            "causal_action_ids": [item.action_id for item in row.exercises],
                        } for row in inspection.target(self.ari.native_being_id).practice_history],
                    }
            if self.active is not None:
                payload = self.active.imported_prefix.payload()
                timeline = [{
                    "boundary": row["boundary"], "start": float.fromhex(row["start_time"]),
                    "action_ids": list(row["action_ids"]),
                    "provenance": "imported/host-accepted claim; original receipt authenticity not established",
                } for row in payload["boundaries"]]
                if self.active.start_boundary == 7:
                    claim = self.active.imported_run_claim
                    timeline.append({
                        "boundary": 7, "start": 6.0,
                        "action_ids": [claim["action"]["action_id"]],
                        "provenance": "imported/host-accepted claim; original receipt authenticity not established",
                    })
                if inspection is not None and self.active.start_boundary == 6:
                    composed = _compose_committed_inspection(self.active)
                    timeline = [{
                        "boundary": row.boundary, "start": row.start,
                        "action_ids": list(row.action_ids), "provenance": row.provenance,
                    } for row in composed.timeline]
                elif inspection is not None:
                    timeline.extend({
                        "boundary": row.boundary, "start": row.start,
                        "action_ids": list(row.action_ids),
                        "provenance": "native/publisher-issued in this process",
                    } for row in inspection.timeline)
            else:
                timeline = [] if inspection is None else [
                    {"boundary": row.boundary, "start": row.start,
                     "action_ids": list(row.action_ids),
                     "provenance": "native/publisher-issued in this process"}
                    for row in inspection.timeline]
            imported_action = None
            if self.active is not None:
                spot = self.active.imported_history.spot
                imported_action = {
                    "id": spot.action_id, "boundary": spot.resolved_boundary,
                    "outcome": spot.outcome,
                    "provenance": "imported/host-accepted claim; original receipt authenticity not established",
                }
            return {
                "audience": "GM/developer omniscient Reality view; local operator tool, not an auth boundary",
                "time": self.encounter.time, "encounter_id": self.encounter.id,
                "participants": participants,
                "choice": None if choice is None else {
                    "id": choice.id, "state": choice.state,
                    "action_ids": list(choice.action_ids), "first_start": choice.first_start},
                "spot": committed_action, "committed_timeline": timeline,
                "historical_spot_claim": imported_action,
                "historical_run_claim": (None if self.active is None or self.active.imported_run_claim is None
                    else {"id": self.active.imported_run_claim["action"]["action_id"],
                          "boundary": 7,
                          "provenance": "imported/host-accepted claim; original receipt authenticity not established"}),
                "history_mode": "trusted-local continuation" if self.active is not None else "native live Arena",
                "checkpoint_boundary": None if self.active is None else self.active.start_boundary,
                "imported_history_trust": None if self.active is None else self.active.imported_history.trust,
                "run_choice": None if self._run_choice is None else {
                    "id": self._run_choice.id, "state": self._run_choice.state,
                    "action_ids": list(self._run_choice.action_ids),
                },
                "save_available": (self.save_path is not None and not self._saved
                    and ((self.active is None and self.encounter.time == 6
                          and committed_action is not None and committed_action["outcome"] == "success")
                         or (self.active is not None and self.active.start_boundary == 6
                             and self.encounter.time == 7 and committed_action is not None
                             and committed_action["id"] == "npc-arena/action/run-ari-boundary-7"
                             and committed_action["outcome"] == "success"))),
                "save_bundle_kind": ("S7" if self.active is not None and self.active.start_boundary == 6
                                     else "S6"),
                "saved": self._saved,
                "native_receipt_boundaries": [row.boundary for row in self.encounter.__dict__.get("_atomic_interval_history", ())],
                "native_inspection_boundaries": [] if inspection is None else [row.boundary for row in inspection.timeline],
                "rng_unchanged": self.rng.state == self._rng_initial,
            }
    def observer_view(self, observer_id):
        """Observer-specific Awareness only: no position or direct Reality lookup."""
        with self._lock:
            bindings = {self.ari.native_being_id: self.ari,
                        self.bex.native_being_id: self.bex}
            if observer_id not in bindings:
                raise ArenaRequestError("unknown observer")
            known = self.encounter.aware_beings(observer_id)
            return {
                "audience": "observer-scoped Awareness projection; not a Reality or location view",
                "observer": bindings[observer_id].display_name,
                "time": self.encounter.time,
                "aware_participants": [bindings[item].display_name for item in known if item in bindings],
            }
    def submit_spot(self):
        """Use native proposal, validation, and whole-choice acceptance."""
        with self._lock:
            if self.encounter.time != 0 or self.encounter.last_processed_boundary != 0:
                raise ArenaRequestError("Spot must be submitted before the first Encounter step")
            if self._choice is not None:
                raise ArenaRequestError("the Arena Spot Choice was already submitted")
            action = SpotAction(
                self.world, self.ari.native_being_id, self.bex.native_being_id,
                start_time=0, duration=6, die_roll=self.die_roll,
                id="npc-arena/action/spot-ari-bex")
            # The native convenience adapter performs the same complete-set
            # validation and produces the closed ChoiceBook state required by
            # the existing B2 capture contract.
            choice = self.encounter.schedule_choice((action,))
            self._spot, self._choice = action, choice
            return {"choice_id": choice.id, "state": choice.state,
                    "action_ids": list(choice.action_ids)}
    def advance_one_second(self):
        with self._lock:
            limit = (6 if self.active is None else self.active.start_boundary + 1)
            if self.encounter.time >= limit:
                raise ArenaRequestError(f"this bounded Arena ends at boundary {limit}")
            if self.active is not None and self.encounter.time == self.active.start_boundary and self._run_choice is None:
                raise ArenaRequestError(f"submit the one allowlisted Run Choice before advancing boundary {limit}")
            before = self.encounter.time
            if self.active is not None:
                self.encounter.step(1, velocities={
                    self.ari.native_being_id: (1, 0, 0),
                    self.bex.native_being_id: (0, 0, 0),
                })
            else:
                self.encounter.step(1)
            if self.encounter.time != before + 1:
                raise RuntimeError("native Encounter did not advance exactly one second")
            return self.gm_view()
    def save_supported_state(self):
        """Save only a successfully committed, quiescent native boundary 6."""
        with self._lock:
            if self.save_path is None or self.active is not None:
                raise ArenaRequestError("this Arena process has no configured initial-state save destination")
            if self._saved:
                raise ArenaRequestError("this Arena boundary-6 state was already saved")
            if self.encounter.time != 6 or self.encounter.last_processed_boundary != 6:
                raise ArenaRequestError("save requires the committed boundary-6 state")
            if (self.encounter.pending_action_list or self.encounter.__dict__.get("_dispatching")
                    or self.encounter.__dict__.get("_advancing") or self.encounter.__dict__.get("_running")):
                raise ArenaRequestError("save requires quiescent Action scheduling")
            inspection = self.encounter.inspect_committed(6)
            spot = inspection.action("npc-arena/action/spot-ari-bex")
            if spot.facts.outcome != "success" or spot.resolved_boundary != 6:
                raise ArenaRequestError("only the successful boundary-6 Spot case is saveable")
            if self._choice is None or self.encounter.get_choice(self._choice.id).state != "finished":
                raise ArenaRequestError("native Spot Choice is not finished at boundary 6")
            summary = dict(self.scenario)
            prefix = capture_arena_history_prefix(summary)
            candidate = capture_arena_post_spot_state(summary, prefix)
            wire = encode_local_bundle(prefix, candidate)
            try:
                destination = write_local_bundle(
                    self.save_path, wire,
                    repository_root=Path(__file__).resolve().parents[1])
            except ArenaLocalCheckpointRejected as exc:
                raise ArenaRequestError(str(exc)) from exc
            self._saved = True
            return {
                "saved": True,
                "path": str(destination),
                "bundle_schema": "universe.arena.operator-bundle/1",
                "history_prefix_sha256": prefix.content_sha256,
                "state_candidate_sha256": candidate.content_sha256,
                "historical_trust": "untrusted data until separately host-admitted",
            }
    def save_s7_state(self):
        """Save the native boundary-7 claim as a separate non-overwriting S7 file."""
        with self._lock:
            if (self.save_path is None or self.active is None or self.active.start_boundary != 6
                    or self._base_bundle_wire is None):
                raise ArenaRequestError("S7 save requires the approved S6 continuation process")
            if self._saved:
                raise ArenaRequestError("this process already saved its supported continuation state")
            if self.encounter.time != 7 or self.encounter.last_processed_boundary != 7:
                raise ArenaRequestError("S7 save requires committed boundary 7")
            if self._run_choice is None or self.encounter.get_choice(self._run_choice.id).state != "finished":
                raise ArenaRequestError("boundary-7 Run Choice is not finished")
            candidate = capture_s7_candidate(self._base_bundle_wire, self.active)
            try:
                destination = write_local_bundle(
                    self.save_path, candidate.to_bytes(),
                    repository_root=Path(__file__).resolve().parents[1])
            except ArenaLocalCheckpointRejected as exc:
                raise ArenaRequestError(str(exc)) from exc
            self._saved = True
            return {"saved": True, "path": str(destination),
                    "bundle_schema": "universe.arena.local-s7-claim/1",
                    "content_sha256": candidate.content_sha256,
                    "historical_trust": "boundaries 1-7 remain host-accepted claims; no historical receipt authority carried"}
    def submit_run(self):
        """Accept the one fixed native Ari +X Run at the imported time-6 fence."""
        with self._lock:
            if self.active is None or self.encounter.time != self.active.start_boundary:
                raise ArenaRequestError("the supported Run Choice is available only at an approved checkpoint boundary")
            if self._run_choice is not None:
                raise ArenaRequestError("the boundary-7 Run Choice was already submitted")
            action = RunAction(
                self.world, self.ari.native_being_id, self.active.start_boundary, 1, 0.5,
                experience=4, id=f"npc-arena/action/run-ari-boundary-{self.active.start_boundary + 1}")
            self._run_choice = self.encounter.schedule_choice((action,))
            self._run = action
            return {"choice_id": self._run_choice.id, "state": self._run_choice.state,
                    "action_ids": list(self._run_choice.action_ids),
                    "provenance": "new operator-submitted native Choice; boundary 7 not yet committed"}
_PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Universe Encounter Arena</title><style>
body{font:16px system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#202533}.tag{background:#f1e8d3;padding:.65rem;border-left:4px solid #a87520}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}section{border:1px solid #ccd2da;border-radius:8px;padding:1rem}button{padding:.6rem 1rem;margin:.4rem .4rem .4rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f7f8;padding:.8rem}svg{width:100%;height:230px;background:#f5f8fb;border:1px solid #d3dae2}
</style><h1>Universe Encounter Arena</h1><p class="tag"><b>Local GM/developer tool.</b> The GM panel is omniscient Reality inspection. Ari and Bex panels are separate observer Awareness projections. This localhost page is not an authentication boundary.</p>
<section><h2>GM / developer Reality view</h2><p id="clock"></p><p id="trust"></p><svg viewBox="0 0 520 220" role="img" aria-label="Cartesian Arena map"><line x1="30" y1="180" x2="500" y2="180" stroke="#667"/><line x1="30" y1="20" x2="30" y2="180" stroke="#667"/><g id="markers"></g></svg><pre id="participants"></pre><p id="instructions">Supported operation: Ari Spots Bex (GM-directed target; fixed scenario roll). Submit before stepping, then advance one second per click. The six-second Action commits at boundary 6.</p><button id="spot">Submit Ari → Bex Spot Choice</button><button id="save" hidden>Save supported Arena state</button><button id="run" hidden>Submit Ari Run +X Choice</button><button id="advance">Advance one second</button><p id="message" role="status"></p><h3>Choice and committed result</h3><pre id="choice"></pre><h3>Boundary history and provenance</h3><pre id="timeline"></pre></section>
<div class="grid"><section><h2>Ari observer projection</h2><pre id="ari"></pre></section><section><h2>Bex observer projection</h2><pre id="bex"></pre></section></div>
<script>
async function req(path,method='GET',body){const o={method,headers:{}};if(body!==undefined){o.headers['Content-Type']='application/json';o.body=JSON.stringify(body)}const r=await fetch(path,o),d=await r.json();if(!r.ok)throw Error(d.error||('HTTP '+r.status));return d}
function show(id,v){document.getElementById(id).textContent=JSON.stringify(v,null,2)}
function draw(rows){const g=document.getElementById('markers');while(g.firstChild)g.removeChild(g.firstChild);for(const p of rows){const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',String(50+Number(p.position.x)*100));c.setAttribute('cy',String(170-Number(p.position.y)*100));c.setAttribute('r','8');c.setAttribute('fill',p.name==='Ari'?'#316ab0':'#bd573d');g.appendChild(c);const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',String(62+Number(p.position.x)*100));t.setAttribute('y',String(174-Number(p.position.y)*100));t.textContent=p.name;g.appendChild(t)}}
async function refresh(){const g=await req('/api/gm');document.getElementById('clock').textContent='Encounter time: '+g.time+' s';document.getElementById('trust').textContent=g.imported_history_trust||'';draw(g.participants);show('participants',g.participants);show('choice',{native_choice:g.choice,run_choice:g.run_choice,imported_spot_claim:g.historical_spot_claim,imported_run_claim:g.historical_run_claim,committed_action:g.spot});show('timeline',g.committed_timeline);show('ari',await req('/api/observer/ari'));show('bex',await req('/api/observer/bex'));document.getElementById('spot').hidden=g.history_mode!=='native live Arena';document.getElementById('spot').disabled=!!g.choice||g.time!==0;document.getElementById('save').hidden=!g.save_available&&!g.saved;document.getElementById('save').disabled=!g.save_available;document.getElementById('save').textContent=g.save_bundle_kind==='S7'?'Save boundary-7 continuation as S7':'Save supported Arena state as S6';document.getElementById('run').hidden=g.history_mode!=='trusted-local continuation';document.getElementById('run').disabled=g.time!==g.checkpoint_boundary||!!g.run_choice;document.getElementById('advance').disabled=(g.history_mode==='native live Arena'?g.time>=6:g.time>=g.checkpoint_boundary+1)||(g.history_mode==='trusted-local continuation'&&g.time===g.checkpoint_boundary&&!g.run_choice);document.getElementById('instructions').textContent=g.history_mode==='native live Arena'?'Ari Spots Bex; advance through boundary 6, then save S6.':(g.checkpoint_boundary===6?'S6 is host-accepted local initial state. Submit Ari Run +X, commit boundary 7, then save S7 to a second file.':'S7 boundaries 1–7 are imported claims. Submit one native Ari Run +X and commit boundary 8.')}
document.getElementById('spot').onclick=async()=>{try{await req('/api/spot','POST',{operation:'ari_spots_bex'});document.getElementById('message').textContent='Choice accepted by native Encounter ChoiceBook.';await refresh()}catch(e){document.getElementById('message').textContent=e.message}};
document.getElementById('advance').onclick=async()=>{try{await req('/api/advance','POST',{seconds:1});document.getElementById('message').textContent='Advanced one native Encounter second.';await refresh()}catch(e){document.getElementById('message').textContent=e.message}};refresh().catch(e=>document.getElementById('message').textContent=e.message);
document.getElementById('save').onclick=async()=>{try{const r=await req('/api/save','POST',{});document.getElementById('message').textContent='Saved '+r.bundle_schema+'; imported history remains a host-accepted claim and requires separate approval.';await refresh()}catch(e){document.getElementById('message').textContent=e.message}};
document.getElementById('run').onclick=async()=>{try{await req('/api/run','POST',{operation:'ari_run_plus_x'});document.getElementById('message').textContent='Native Run Choice accepted. Advance one second to publish boundary 7.';await refresh()}catch(e){document.getElementById('message').textContent=e.message}};
</script></html>'''
_GENERATED_PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Universe Arena</title><meta name="arena-ui-generation" content="005D"><style>
body{font:16px system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#202533}section{border:1px solid #ccd2da;border-radius:8px;padding:1rem;margin:1rem 0}.sheet-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.5rem 1rem}.sheet-group{border-top:1px solid #d5dce5;padding-top:.5rem}.sheet-group h3{margin:.5rem 0}.sheet-field{margin:.3rem 0}.sheet-item{display:block;margin:.35rem 0}.row{display:flex;flex-wrap:wrap;gap:1rem;align-items:end}label{display:grid;gap:.3rem}input{font:inherit;padding:.45rem;width:12rem}button{font:inherit;padding:.55rem .9rem}button:disabled{opacity:.5}canvas{width:100%;height:min(65vh,520px);background:#f5f8fb;border:1px solid #d3dae2}.status{padding:.7rem;background:#f1e8d3;border-left:4px solid #a87520}#error{color:#9a241e;min-height:1.3em}dialog{width:min(680px,92vw);max-height:82vh;overflow:auto;border:1px solid #9ba8b8;border-radius:10px;padding:1rem 1.25rem;color:#202533}dialog::backdrop{background:#15223588}dialog[open]{box-shadow:0 12px 40px #15223555}.dialog-heading{display:flex;justify-content:space-between;align-items:center;gap:1rem}.dialog-heading h2{margin:.3rem 0}.action-selector{margin-top:1rem;border-top:1px solid #d5dce5;padding-top:.75rem}.action-selector>summary{cursor:pointer;font-size:1.1rem;font-weight:650}.action-legend,.action-reason{font-size:.9rem;color:#505c6b}.action-list{max-height:32vh;overflow:auto;border:1px solid #d5dce5;border-radius:6px;padding:.4rem .7rem}.action-list h4{margin:.6rem 0 .2rem}.action-row{display:grid;grid-template-columns:minmax(7rem,10rem) 8rem minmax(12rem,1fr);gap:.4rem .7rem;align-items:start;padding:.3rem 0;border-top:1px solid #edf0f4}.action-row button{padding:.25rem .45rem;text-align:left}.action-status{font-size:.85rem;font-weight:650;text-transform:capitalize}.action-status.available{color:#176438}.action-status.unavailable{color:#805812}.action-status.not_implemented{color:#66717f}.action-target{grid-column:2/4;font-size:.85rem;color:#34445a}@media(max-width:650px){.action-row{grid-template-columns:1fr 1fr}.action-reason{grid-column:1/-1}.action-target{grid-column:1/-1}}
</style><h1>Universe Arena</h1><p class="status">Local generated Arena. Unobstructed Beings and realized Objects are visible from native Encounter time zero. No Encounter starts until Generate Encounter succeeds.</p>
<section><h2>Generate Encounter</h2><div class="row"><label>Starting XP<input id="xp" type="text" inputmode="numeric" autocomplete="off" value="0"></label><label>Width (hex columns)<input id="width" type="text" inputmode="numeric" autocomplete="off" value="5"></label><label>Height (hex rows)<input id="height" type="text" inputmode="numeric" autocomplete="off" value="5"></label><button id="generate" disabled>Generate Encounter</button><button id="load" disabled title="General save/load is not implemented">Load unavailable</button></div><p id="error" role="alert"></p></section>
<section><h2 id="encounterTitle">No active Encounter</h2><div class="row"><p id="clock">Time: —</p><label>Encounter display name<input id="encounterName" maxlength="40" disabled></label><button id="saveEncounterName" disabled>Apply name</button><label>Your Being name<input id="playerName" maxlength="40" disabled></label><button id="savePlayerName" disabled>Apply name</button></div><canvas id="map" tabindex="0" aria-label="Initial one-yard hex map"></canvas><p id="mapCaption">Each regular flat-top hex measures one yard (0.9144 m) between opposite sides. Columns increase east; rows increase north in the odd-column offset layout. Choose a rate and facing policy, then click a destination hex. While a plan is active, changing either option updates that destination immediately; Advance waits for those updates. The accepted plan and selected options are shown separately. Click visible entity markers to inspect them; Pick up is enabled only in the target hex. Close any open dialog to return to the map. Native rules determine actual movement distance.</p><div class="row"><label>Selected movement rate<select id="rate" disabled><option value="walk">Walk</option><option value="hustle">Hustle</option><option value="jog">Jog</option><option value="run">Run</option><option value="sprint">Sprint</option></select></label><label>Selected facing policy<select id="facingPolicy" disabled><option value="turn">Turn and move</option><option value="maintain">Maintain facing</option></select></label><button id="stop" disabled>Stop movement</button></div><p id="player"></p><p id="movementStatus"></p><button id="spot" disabled title="Native Spot requires Being geometry">Spot unavailable</button><p id="spotReason"></p><button id="run" disabled>Choose Run instead</button><button id="advance" disabled>Advance 1 second</button><p id="actionResult">Select a destination, rate, and facing policy; the first movement selection starts the native Encounter.</p><button id="characterButton" disabled>Character</button></section><section><h2>Visible entities</h2><div id="entities"></div></section><dialog id="entityDialog" aria-labelledby="dialogTitle"><div class="dialog-heading"><h2 id="dialogTitle">Entity details</h2><button id="dialogClose" type="button">Close</button></div><p class="dialog-map-hint">Close this dialog to return to the map and movement controls.</p><div id="dialogBody"></div></dialog>
<script>
const $=id=>document.getElementById(id), fields=[$('xp'),$('width'),$('height')];
const traceEnabled=__ARENA_TRACE_ENABLED__;let clientSequence=0;
function traceUI(event,detail={}){if(!traceEnabled)return null;const seq=++clientSequence;const body={seq,event,...detail};fetch('/api/generated/trace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(()=>{});return seq}
window.addEventListener('error',()=>traceUI('page_script_error'));
function exactInteger(s,min){if(!/^[0-9]+$/.test(s))return false;const n=s.replace(/^0+(?=.)/,'');const m=String(min);return n.length>m.length||(n.length===m.length&&n>=m)}
function validate(){ $('generate').disabled=!(exactInteger($('xp').value,0)&&exactInteger($('width').value,5)&&exactInteger($('height').value,5)); }
fields.forEach(x=>x.addEventListener('input',validate)); validate();
async function req(path,body,sequence=null){const headers=body===undefined?{}:{'Content-Type':'application/json'};if(sequence!==null)headers['X-Arena-Client-Seq']=String(sequence);const r=await fetch(path,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});const d=await r.json();if(!r.ok){const error=Error(d.error||('HTTP '+r.status));if(d.movement_refusal)error.movementRefusal=d.movement_refusal;throw error}return d}
function draw(s){const c=$('map'),ctx=c.getContext('2d'),dpr=Math.min(window.devicePixelRatio||1,2),w=c.clientWidth,h=c.clientHeight;c.width=Math.max(1,Math.round(w*dpr));c.height=Math.max(1,Math.round(h*dpr));ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(s.state!=='active')return;const m=s.map,mw=m.width_cells,mh=m.height_cells,pad=12,minX=0,maxX=m.origin_offset_meters[0]+(mw-1)*m.column_step_meters+m.hex_vertex_offsets_meters[0][0],minY=0,maxY=mh*m.row_step_meters+(mw>1?m.odd_column_offset_meters:0),sx=(w-2*pad)/(maxX-minX),sy=(h-2*pad)/(maxY-minY),scale=Math.min(sx,sy),ox=(w-(maxX-minX)*scale)/2,oy=(h-(maxY-minY)*scale)/2,toX=x=>ox+(x-minX)*scale,toY=y=>h-oy-(y-minY)*scale;let columns=m.column_row_ranges;if(columns===null){columns=[];for(let col=0;col<mw;col++)columns.push([col,[[0,mh-1]]]);}ctx.strokeStyle='#d5dce5';ctx.lineWidth=1;ctx.beginPath();for(const [col,ranges] of columns){for(const [first,last] of ranges){for(let row=first;row<=last;row++){const cx=m.origin_offset_meters[0]+col*m.column_step_meters,cy=m.origin_offset_meters[1]+row*m.row_step_meters+(col%2)*m.odd_column_offset_meters;for(let i=0;i<6;i++){const a=m.hex_vertex_offsets_meters[i],b=m.hex_vertex_offsets_meters[(i+1)%6];if(i===0)ctx.moveTo(toX(cx+a[0]),toY(cy+a[1]));ctx.lineTo(toX(cx+b[0]),toY(cy+b[1]));}ctx.closePath();}}}ctx.stroke();const p=s.player.position_meters,px=toX(p.x),py=toY(p.y);ctx.beginPath();ctx.arc(px,py,Math.max(7,Math.min(13,scale*.22)),0,Math.PI*2);ctx.fillStyle='#316ab0';ctx.fill();ctx.fillStyle='white';ctx.font='bold 12px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText((s.player.name.trim()[0]||'P').toUpperCase(),px,py);const a=s.player.hex_facing*Math.PI/6;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px+Math.cos(a)*22,py-Math.sin(a)*22);ctx.strokeStyle='#173b67';ctx.lineWidth=3;ctx.stroke();}
let mapView=null;
function draw(s){const c=$('map'),ctx=c.getContext('2d'),dpr=Math.min(window.devicePixelRatio||1,2),w=c.clientWidth,h=c.clientHeight;c.width=Math.max(1,Math.round(w*dpr));c.height=Math.max(1,Math.round(h*dpr));ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);mapView=null;if(s.state!=='active')return;const m=s.map,mw=m.width_cells,mh=m.height_cells,pad=12,minX=0,maxX=m.origin_offset_meters[0]+(mw-1)*m.column_step_meters+m.hex_vertex_offsets_meters[0][0],minY=0,maxY=mh*m.row_step_meters+(mw>1?m.odd_column_offset_meters:0),sx=(w-2*pad)/(maxX-minX),sy=(h-2*pad)/(maxY-minY),scale=Math.min(sx,sy),ox=(w-(maxX-minX)*scale)/2,oy=(h-(maxY-minY)*scale)/2,toX=x=>ox+(x-minX)*scale,toY=y=>h-oy-(y-minY)*scale;mapView={m,w,h,minX,minY,scale,ox,oy,toX,toY};for(const e of (s.entities||[])){if(!e.position_meters)continue;const ex=toX(e.position_meters.x),ey=toY(e.position_meters.y);ctx.fillStyle=e.category==='being'?'#9a3d55':'#7b5a20';ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();if(e.category==='being')ctx.arc(ex,ey,8,0,Math.PI*2);else{ctx.moveTo(ex,ey-9);ctx.lineTo(ex+8,ey+7);ctx.lineTo(ex-8,ey+7);ctx.closePath()}ctx.fill();ctx.stroke();ctx.fillStyle='#202533';ctx.font='11px system-ui';ctx.textAlign='left';ctx.fillText(e.name,ex+10,ey-8)}let columns=m.column_row_ranges;if(columns===null){columns=[];for(let col=0;col<mw;col++)columns.push([col,[[0,mh-1]]]);}ctx.strokeStyle='#d5dce5';ctx.lineWidth=1;ctx.beginPath();for(const [col,ranges] of columns){for(const [first,last] of ranges){for(let row=first;row<=last;row++){const cx=m.origin_offset_meters[0]+col*m.column_step_meters,cy=m.origin_offset_meters[1]+row*m.row_step_meters+(col%2)*m.odd_column_offset_meters;for(let i=0;i<6;i++){const a=m.hex_vertex_offsets_meters[i],b=m.hex_vertex_offsets_meters[(i+1)%6];if(i===0)ctx.moveTo(toX(cx+a[0]),toY(cy+a[1]));ctx.lineTo(toX(cx+b[0]),toY(cy+b[1]));}ctx.closePath();}}}ctx.stroke();const p=s.player.position_meters,px=toX(p.x),py=toY(p.y),plan=s.movement_plan;if(plan){const d=plan.destination_position_meters,dx=toX(d.x),dy=toY(d.y);ctx.save();ctx.setLineDash([6,4]);ctx.strokeStyle='#b45d16';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(dx,dy);ctx.stroke();ctx.restore();ctx.beginPath();ctx.arc(dx,dy,7,0,Math.PI*2);ctx.strokeStyle='#b45d16';ctx.lineWidth=2;ctx.stroke();}ctx.beginPath();ctx.arc(px,py,Math.max(7,Math.min(13,scale*.22)),0,Math.PI*2);ctx.fillStyle='#316ab0';ctx.fill();ctx.fillStyle='white';ctx.font='bold 12px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText((s.player.name.trim()[0]||'P').toUpperCase(),px,py);const a=s.player.hex_facing*Math.PI/6;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px+Math.cos(a)*22,py-Math.sin(a)*22);ctx.strokeStyle='#173b67';ctx.lineWidth=3;ctx.stroke();}
let popupKind=null,popupTrigger=null;
function conciseEntityLabel(e){const name=(e.name||'').trim(),type=(e.type||'').trim(),identity=name&&type&&name.toLowerCase()!==type.toLowerCase()?`${name} — ${type}`:(name||type||'Entity');return `${identity} · ${e.present_state}${e.cell?` · hex (${e.cell.column}, ${e.cell.row})`:''}`}
function inspectEntity(handle,trigger){const sequence=traceUI('entity_selected');return serializeMutation(async()=>{try{popupKind='entity';if(!$('entityDialog').open)popupTrigger=trigger;show(await req('/api/generated/inspect',{handle},sequence));if(!$('entityDialog').open)$('entityDialog').showModal();$('dialogClose').focus()}catch(error){$('error').textContent=error.message;try{await refresh()}catch(_){}}})}
function openCharacterPopup(trigger){if(!currentView||!currentView.character)return;popupKind='character';popupTrigger=trigger;const sequence=traceUI('character_sheet_opened');if(sequence!==null){}renderPopup(currentView);if(!$('entityDialog').open)$('entityDialog').showModal();$('dialogClose').focus()}
function closeEntityPopup(){const dialog=$('entityDialog');if(dialog.open)dialog.close();}
$('dialogClose').addEventListener('click',closeEntityPopup);
$('entityDialog').addEventListener('close',()=>{popupKind=null;const trigger=popupTrigger;popupTrigger=null;if(trigger&&typeof trigger.focus==='function')trigger.focus()});
$('characterButton').addEventListener('click',event=>openCharacterPopup(event.currentTarget));
function renderEntities(s){const root=$('entities');root.replaceChildren();for(const e of (s.entities||[])){const b=document.createElement('button');b.type='button';b.textContent=conciseEntityLabel(e);b.dataset.handle=e.handle;b.addEventListener('click',()=>inspectEntity(e.handle,b));root.appendChild(b)}}
function renderCharacterSheet(character,actionCatalog){const body=$('dialogBody');body.replaceChildren();if(!character)return;const grid=document.createElement('div');grid.className='sheet-grid';body.appendChild(grid);const group=title=>{const root=document.createElement('div');root.className='sheet-group';const heading=document.createElement('h3');heading.textContent=title;root.appendChild(heading);grid.appendChild(root);return root};const field=(root,label,value)=>{const row=document.createElement('p');row.className='sheet-field';row.textContent=`${label}: ${value}`;root.appendChild(row)};const identity=character.identity,identityGroup=group('Identity and experience');field(identityGroup,'Name',identity.display_name);field(identityGroup,'Native type / race',`${identity.native_type} / ${identity.race||'unknown'}`);field(identityGroup,'Age',identity.age===null?identity.age_status:identity.age);field(identityGroup,'Class / levels',identity.class_levels===null?identity.class_levels_status:JSON.stringify(identity.class_levels));field(identityGroup,'Stature',`${identity.stature_inches.toFixed(2)} in`);field(identityGroup,'Body weight',`${identity.body_weight_pounds.toFixed(2)} lb`);field(identityGroup,'Total native XP',character.experience.total);field(identityGroup,'Class XP',character.experience.class_allocation===null?character.experience.class_allocation_status:JSON.stringify(character.experience.class_allocation));const abilityLabels={STR:'Strength',DEX:'Dexterity',CON:'Constitution',INT:'Intelligence',WIS:'Wisdom',CHA:'Charisma',FIT:'Fitness'};const abilityGroup=group('Abilities');for(const a of character.abilities)field(abilityGroup,abilityLabels[a.name]||a.name,a.score);const skillGroup=group('Skills and recorded practice');for(const section of character.skills){const title=document.createElement('p');title.textContent=section.kind==='weapon'?'Weapon skills':'Ordinary skills';skillGroup.appendChild(title);if(!section.skills.length){field(skillGroup,'Ranks','None recorded');continue}for(const skill of section.skills)field(skillGroup,skill.name,`rank ${skill.rank} · ${skill.practice_experience} practice XP`)}const condition=character.condition,conditionGroup=group('Condition');field(conditionGroup,'Hit points',`${condition.hit_points_current} · ${condition.hit_points_maximum===null?condition.hit_points_maximum_status:'maximum '+condition.hit_points_maximum}`);field(conditionGroup,'Fatigue level',`${condition.legacy_fatigue_level} (legacy native field)`);field(conditionGroup,'Physical fatigue reserves',`Q ${condition.physical_fatigue_reserves.q} · B ${condition.physical_fatigue_reserves.b} · profile ${condition.physical_fatigue_reserves.profile_status}`);field(conditionGroup,'Posture',condition.posture||'unknown');field(conditionGroup,'Native states',Object.keys(condition.states).length?Object.entries(condition.states).map(([name,value])=>`${name}: ${value?'active':'inactive'}`).join(', '):'No active native states');const anatomy=character.anatomy,anatomyGroup=group('Hands');if(anatomy.status==='available'){for(const hand of anatomy.hands)field(anatomyGroup,hand.name,hand.occupancy==='empty'?'empty':`${hand.object.name} — ${hand.object.type}`)}else{field(anatomyGroup,'Hands',anatomy.status==='unrepresented'?'Unknown / not represented':'Unavailable from native state')}const movement=character.movement,movementGroup=group('Position and movement');field(movementGroup,'Position',`(${movement.position_meters.x}, ${movement.position_meters.y}, ${movement.position_meters.z}) m`);field(movementGroup,'Hex',movement.cell?`(${movement.cell.column}, ${movement.cell.row})`:'outside map footprint');field(movementGroup,'Facing',movement.hex_facing===null?'unknown':`${movement.hex_facing} / 12`);field(movementGroup,'Posture',movement.posture||'unknown');field(movementGroup,'Movement plan',movement.selected_plan?`${movement.selected_plan.rate} · ${movement.selected_plan.facing_policy} · destination (${movement.selected_plan.destination_cell.column}, ${movement.selected_plan.destination_cell.row}) · ${movement.selected_plan.remaining_distance_meters} m remaining`:'none');field(movementGroup,'Rate note',movement.speed_status);const inventory=character.inventory,inventoryRoot=document.createElement('section');inventoryRoot.className='sheet-inventory';const heading=document.createElement('h3');heading.textContent='Carried Objects and equipment';inventoryRoot.appendChild(heading);body.appendChild(inventoryRoot);if(inventory.status!=='available'){const unavailable=document.createElement('p');unavailable.textContent=inventory.encumbrance_status;inventoryRoot.appendChild(unavailable)}else if(!inventory.items.length){const empty=document.createElement('p');empty.textContent='No items carried';inventoryRoot.appendChild(empty)}else for(const item of inventory.items){const button=document.createElement('button');button.type='button';button.className='sheet-item';button.textContent=`${conciseEntityLabel({name:item.name,type:item.type,present_state:item.status})} · ${item.kind} · ${item.weight_pounds} lb`;button.dataset.handle=item.handle;button.addEventListener('click',()=>inspectEntity(item.handle,button));inventoryRoot.appendChild(button)}if(inventory.status==='available'){const total=document.createElement('p');total.textContent=`Represented carried weight: ${inventory.carried_weight_pounds} lb. ${inventory.encumbrance_status}`;inventoryRoot.appendChild(total)}renderActionSelector(actionCatalog)}
let actionSelectorOpen=false;
function renderActionSelector(catalog){if(!catalog)return;const details=document.createElement('details');details.id='actionSelector';details.className='action-selector';details.open=actionSelectorOpen;details.addEventListener('toggle',()=>{actionSelectorOpen=details.open});const summary=document.createElement('summary');summary.textContent=`Actions · ${catalog.entries.length} potential`;details.appendChild(summary);const legend=document.createElement('p');legend.className='action-legend';legend.textContent='Available can be selected now · Unavailable has a supported Action blocked by current state · Not implemented has no connected Arena Action contract.';details.appendChild(legend);const list=document.createElement('div');list.className='action-list';let activeGroup=null;for(const action of catalog.entries){if(action.group!==activeGroup){activeGroup=action.group;const group=document.createElement('h4');group.textContent=activeGroup;list.appendChild(group)}const row=document.createElement('div');row.className='action-row';const button=document.createElement('button');button.type='button';button.textContent=action.display_name||action.name;button.disabled=action.status!=='available';button.title=action.reason;if(action.name==='Run'&&action.status==='available')button.addEventListener('click',chooseRunAction);if(action.name==='Pick up'&&action.status==='available'&&action.target)button.addEventListener('click',()=>submitPickup(action.target.handle));if(action.name==='Run')button.id='actionRun';if(action.name==='Pick up')button.id='actionPickup';if(action.name.toLowerCase()==='ready weapon'){button.id='actionReadyWeapon';if(action.target&&action.hands&&action.hands.length){const hand=document.createElement('select');hand.id='readyWeaponHand';hand.setAttribute('aria-label','Free native hand');for(const name of action.hands){const option=document.createElement('option');option.value=name;option.textContent=name;hand.appendChild(option)}row.appendChild(hand);button.addEventListener('click',()=>submitReadyWeapon(action.target.handle,hand.value))}}row.appendChild(button);const status=document.createElement('span');status.className=`action-status ${action.status}`;status.textContent=action.status.replace('_',' ');row.appendChild(status);const reason=document.createElement('span');reason.className='action-reason';reason.textContent=action.reason;row.appendChild(reason);if((action.name==='Pick up'||action.name.toLowerCase()==='ready weapon')&&action.target){const target=document.createElement('span');target.className='action-target';target.textContent=`Target: ${conciseEntityLabel(action.target)}`;row.appendChild(target)}list.appendChild(row)}details.appendChild(list);$('dialogBody').appendChild(details)}
function submitPickup(handle){const sequence=traceUI('pickup_clicked');return serializeMutation(async()=>{try{show(await req('/api/generated/pickup',{handle},sequence));$('error').textContent='Native Pick up Choice accepted; advance one second to resolve.'}catch(error){$('error').textContent=error.message;await refresh()}})}
function submitReadyWeapon(handle,hand){const sequence=traceUI('ready_weapon_clicked');return serializeMutation(async()=>{try{show(await req('/api/generated/ready-weapon',{handle,hand},sequence));$('error').textContent=`Native weapon draw Choice accepted for ${hand}; advance two seconds to resolve.`}catch(error){$('error').textContent=error.message;await refresh()}})}
function chooseRunAction(){const sequence=traceUI('run_clicked');return serializeMutation(async()=>{try{show(await req('/api/generated/run',{},sequence));$('error').textContent='Native Run Choice accepted; Encounter activated.'}catch(error){$('error').textContent=error.message;await refresh()}})}
function renderPopup(s){const body=$('dialogBody');body.replaceChildren();if(popupKind==='character'&&s.character){$('dialogTitle').textContent='Your Being — Character';renderCharacterSheet(s.character,s.action_catalog);return}const e=s.selected_entity;if(popupKind!=='entity'||!e){closeEntityPopup();return}$('dialogTitle').textContent=conciseEntityLabel(e).split(' · ')[0];const addField=(label,value)=>{const p=document.createElement('p');p.textContent=`${label}: ${value}`;body.appendChild(p)};addField('Name',e.name);addField('Type',e.type);addField('Entity',e.category==='being'?'Being':'Object');addField('State',e.present_state);if(e.position_meters)addField('Position',`(${e.position_meters.x}, ${e.position_meters.y}, ${e.position_meters.z}) m`);if(e.cell)addField('Hex',`(${e.cell.column}, ${e.cell.row})`);if(e.category==='object')addField('Weight','Unavailable from observer evidence');const editor=document.createElement('div');editor.className='row';const label=document.createElement('label');label.textContent='Display name';const input=document.createElement('input');input.id='entityName';input.maxLength=40;input.value=e.name;label.appendChild(input);const rename=document.createElement('button');rename.id='renameEntity';rename.type='button';rename.textContent='Apply display name';rename.addEventListener('click',async()=>{const sequence=traceUI('rename_entity_clicked');await serializeMutation(async()=>{try{show(await req('/api/generated/rename-entity',{handle:e.handle,name:input.value},sequence));$('error').textContent='Display name updated for this Arena session.'}catch(error){$('error').textContent=error.message;await refresh()}})});editor.append(label,rename);body.appendChild(editor);if(e.category==='object'){const pickup=document.createElement('button');pickup.id='pickup';pickup.type='button';pickup.textContent='Pick up';pickup.disabled=!e.pickup_available;pickup.title=e.pickup_available?'':e.pickup_unavailable_reason;pickup.addEventListener('click',()=>submitPickup(e.handle));body.appendChild(pickup);const status=document.createElement('p');status.id='pickupStatus';status.textContent=e.pickup_available?'Native one-second Pick up is available for this Object.':e.pickup_unavailable_reason;body.appendChild(status)}}
function show(s){renderEntities(s);const active=s.state==='active';$('characterButton').disabled=!s.character;$('encounterTitle').textContent=active?s.encounter_name:'No active Encounter';$('clock').textContent=active?'Native Encounter time: '+s.time_seconds+' seconds':'Time: —';$('encounterName').disabled=!active;$('playerName').disabled=!active;$('saveEncounterName').disabled=!active;$('savePlayerName').disabled=!active;$('run').disabled=!s.run_available;$('advance').disabled=!s.advance_available;$('rate').disabled=!s.movement_available;$('facingPolicy').disabled=!s.movement_available;$('stop').disabled=!s.movement_plan;if(active){$('encounterName').value=s.encounter_name;$('playerName').value=s.player.name;const p=s.player.position_meters,cell=s.player.cell;$('player').textContent='You: '+s.player.name+' · '+s.player.posture+' · facing '+s.player.hex_facing+' / 12 · '+(cell?('hex ('+cell.column+', '+cell.row+')'):'outside map footprint')+' · native position ('+p.x+', '+p.y+', '+p.z+') m';$('movementStatus').textContent=s.movement_plan?'Destination hex ('+s.movement_plan.destination_cell.column+', '+s.movement_plan.destination_cell.row+') · '+s.movement_plan.rate+' · '+s.movement_plan.facing_policy+' · '+s.movement_plan.remaining_distance_meters+' m remaining · '+s.movement_outcome:(s.movement_available?'Click a hex to choose a destination.':s.movement_reason);$('spotReason').textContent=s.spot_reason;$('actionResult').textContent=s.ready_weapon_action?(s.ready_weapon_action.status==='completed'?'Draw resolved: '+s.ready_weapon_action.outcome+'.':'Native weapon draw Choice accepted; awaiting two seconds.'):s.pickup_action?(s.pickup_action.status==='completed'?'Pick up resolved: '+s.pickup_action.outcome+'.':'Native Pick up Choice accepted; awaiting one second.'):(s.player_action?(s.player_action.status==='completed'?'Run resolved: '+s.player_action.outcome+'.':'Run Choice accepted; awaiting one native second.'):'Movement activation creates no Action or Choice. Choose Run instead only if you explicitly want that Action.');}else{$('player').textContent='';$('movementStatus').textContent='';$('spotReason').textContent=s.spot_reason;$('actionResult').textContent='Generate an Encounter to begin.';$('encounterName').value='';$('playerName').value='';}draw(s);if(popupKind){if(popupKind==='entity'&&!s.selected_entity){closeEntityPopup();return}renderPopup(s)}}
const renderState=show;let currentView=null,viewRevision=0,refreshGeneration=0,mutationQueue=Promise.resolve(),pendingOptionUpdates=0,planUpdateFailure=null;
function updateMovementStatus(note=''){if(!currentView||currentView.state!=='active')return;const plan=currentView.movement_plan,selectedRate=$('rate').value,selectedPolicy=$('facingPolicy').value;if(plan){const selected=`selected ${selectedRate}/${selectedPolicy}`,accepted=`server accepted ${plan.rate}/${plan.facing_policy}`;const differs=selectedRate!==plan.rate||selectedPolicy!==plan.facing_policy;$('movementStatus').textContent=`Destination (${plan.destination_cell.column}, ${plan.destination_cell.row}) · ${accepted} · ${plan.remaining_distance_meters} m remaining · ${selected}${differs?' (not yet accepted)':''}${pendingOptionUpdates?' · update pending':''}${note?' · '+note:''}`;}else if(currentView.movement_outcome==='already_at_destination')$('movementStatus').textContent='Already at that hex center. Choose a different destination.';else if(currentView.movement_outcome==='stopped')$('movementStatus').textContent='Movement stopped at the committed position. Choose a destination to continue.';else if(currentView.movement_outcome==='arrived')$('movementStatus').textContent='Destination reached at the committed native position.';else $('movementStatus').textContent=currentView.movement_available?`No accepted plan. Selected ${selectedRate}/${selectedPolicy}; choose a destination.`:currentView.movement_reason;}
show=function(s){currentView=s;viewRevision++;renderState(s);updateMovementStatus()};
function serializeMutation(operation){const result=mutationQueue.then(operation,operation);mutationQueue=result.catch(()=>{});return result}
async function refresh(){const revision=viewRevision,generation=++refreshGeneration;const state=await req('/api/generated/state');if(revision===viewRevision&&generation===refreshGeneration)show(state)}
async function updatePlanFromSelection(sequence,rate,policy){pendingOptionUpdates++;updateMovementStatus();return serializeMutation(async()=>{try{const plan=currentView&&currentView.movement_plan;if(!plan){planUpdateFailure=null;return}const cell=plan.destination_cell;const state=await req('/api/generated/destination',{...cell,rate,facing_policy:policy},sequence);show(state);planUpdateFailure=null;$('error').textContent=`Movement plan accepted: ${state.movement_plan.rate}/${state.movement_plan.facing_policy}. Native movement limits still apply.`;}catch(error){try{const state=await req('/api/generated/state');show(state)}catch(_){}const plan=currentView&&currentView.movement_plan;planUpdateFailure=true;$('error').textContent=plan?`Plan update refused: ${error.message} Server plan remains ${plan.rate}/${plan.facing_policy}. Advance is held until a plan update succeeds or you choose another destination.`:`Plan update refused: ${error.message}`;}finally{pendingOptionUpdates--;updateMovementStatus()}})}
function optionChanged(event,detail){const sequence=traceUI(event,detail);const rate=$('rate').value,policy=$('facingPolicy').value;updateMovementStatus();return updatePlanFromSelection(sequence,rate,policy).catch(error=>{$('error').textContent=error.message})}
$('rate').addEventListener('change',()=>optionChanged('rate_selected',{rate:$('rate').value}));$('facingPolicy').addEventListener('change',()=>optionChanged('facing_policy_selected',{facing_policy:$('facingPolicy').value}));
$('generate').onclick=async()=>{const sequence=traceUI('generate_clicked');$('error').textContent='Generating…';await serializeMutation(async()=>{try{show(await req('/api/generated/generate',{starting_experience:$('xp').value,width_cells:$('width').value,height_cells:$('height').value},sequence));planUpdateFailure=null;$('error').textContent='Encounter generated at native time zero.'}catch(error){$('error').textContent=error.message;await refresh()}})};
$('saveEncounterName').onclick=async()=>{const sequence=traceUI('encounter_name_apply_clicked');await serializeMutation(async()=>{try{show(await req('/api/generated/encounter-name',{name:$('encounterName').value},sequence));$('error').textContent='Encounter display name updated.'}catch(error){$('error').textContent=error.message}})};
$('savePlayerName').onclick=async()=>{const sequence=traceUI('player_name_apply_clicked');await serializeMutation(async()=>{try{show(await req('/api/generated/player-name',{name:$('playerName').value},sequence));$('error').textContent='Your Being display name updated.'}catch(error){$('error').textContent=error.message}})};
$('run').onclick=chooseRunAction;
$('advance').onclick=async()=>{const sequence=traceUI('advance_clicked');await serializeMutation(async()=>{if(planUpdateFailure){const plan=currentView&&currentView.movement_plan;$('error').textContent=plan?`Advance held: the server plan is still ${plan.rate}/${plan.facing_policy}; correct or reapply the selected options first.`:'Advance held because the movement plan update was refused.';return}try{show(await req('/api/generated/advance',{seconds:1},sequence));$('error').textContent='One native Encounter second committed.';$('error').dataset.refusalCategory=''}catch(error){$('error').textContent=error.message;$('error').dataset.refusalCategory=error.movementRefusal?error.movementRefusal.category:'';await refresh()}})};
function clickedCell(event){if(!mapView)return null;const rect=$('map').getBoundingClientRect(),px=event.clientX-rect.left,py=event.clientY-rect.top,m=mapView.m,x=(px-mapView.ox)/mapView.scale+mapView.minX,y=(mapView.h-mapView.oy-py)/mapView.scale+mapView.minY;let best=null,bestDistance=Infinity;for(let column=0;column<m.width_cells;column++){for(let row=0;row<m.height_cells;row++){const cx=m.origin_offset_meters[0]+column*m.column_step_meters,cy=m.origin_offset_meters[1]+row*m.row_step_meters+(column%2)*m.odd_column_offset_meters,d=Math.hypot(x-cx,y-cy);if(d<bestDistance){bestDistance=d;best={column,row}}}}return best}
$('map').addEventListener('click',async event=>{
  traceUI('canvas_click_received');
  if($('entityDialog').open){traceUI('canvas_modal_blocked');return;}
  if(mapView&&currentView){
    const rect=$('map').getBoundingClientRect(),mx=event.clientX-rect.left,my=event.clientY-rect.top;
    const p=currentView.player.position_meters,pd=Math.hypot(mx-mapView.toX(p.x),my-mapView.toY(p.y));
    if(pd<=18){traceUI('canvas_player_marker_hit');openCharacterPopup($('characterButton'));return;}
    let hit=null,distance=Infinity;
    for(const e of (currentView.entities||[])){
      if(!e.position_meters)continue;
      const d=Math.hypot(mx-mapView.toX(e.position_meters.x),my-mapView.toY(e.position_meters.y));
      if(d<distance){distance=d;hit=e;}
    }
    if(hit&&distance<=18){
      traceUI('canvas_entity_marker_hit',{entity_category:hit.category});
      await inspectEntity(hit.handle,$('map'));return;
    }
  }
  traceUI('canvas_marker_missed');
  const cell=clickedCell(event);
  if(!cell){traceUI('canvas_hex_missed');return;}
  traceUI('canvas_hex_selected',cell);
  const rate=$('rate').value,policy=$('facingPolicy').value;
  if($('rate').disabled){traceUI('destination_request_refused');$('error').textContent='Movement is unavailable for this Encounter state.';return;}
  const sequence=traceUI('destination_request_queued',{...cell,rate,facing_policy:policy});
  await serializeMutation(async()=>{
    try{
      const state=await req('/api/generated/destination',{...cell,rate,facing_policy:policy},sequence);
      traceUI('destination_request_accepted',cell);
      show(state);planUpdateFailure=null;
      $('error').textContent=state.movement_outcome==='already_at_destination'?'That hex is your current position. Choose a different destination.':`Destination plan accepted: ${state.movement_plan.rate}/${state.movement_plan.facing_policy}.`;
    }catch(error){traceUI('destination_request_refused');$('error').textContent=error.message;await refresh();}
  });
});
$('stop').onclick=async()=>{const sequence=traceUI('stop_clicked');await serializeMutation(async()=>{try{show(await req('/api/generated/stop',{},sequence));planUpdateFailure=null;$('error').textContent='Movement plan stopped at the committed boundary.'}catch(error){$('error').textContent=error.message;await refresh()}})};
window.addEventListener('resize',()=>refresh().catch(()=>{}));traceUI('page_script_ready');refresh().catch(error=>$('error').textContent=error.message);
</script></html>'''
def make_handler(session):
    """Create a strict HTTP handler; no caller-selected Action or Entity IDs."""
    class Handler(BaseHTTPRequestHandler):
        server_version = "UniverseArena/1"
        def _send(self, status, payload, content_type="application/json; charset=utf-8"):
            body = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    if content_type.startswith("application/json") else payload.encode("utf-8"))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Arena-UI-Generation", "005D")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            path = urlsplit(self.path).path
            try:
                if isinstance(session, GeneratedArenaSession):
                    if path == "/":
                        page = _GENERATED_PAGE.replace(
                            "__ARENA_TRACE_ENABLED__",
                            "true" if session.trace_ui_enabled else "false")
                        return self._send(200, page, "text/html; charset=utf-8")
                    if path == "/api/generated/state": return self._send(200, session.public_view())
                    return self._send(404, {"error": "unknown generated Arena endpoint"})
                if path == "/": return self._send(200, _PAGE, "text/html; charset=utf-8")
                if path == "/api/gm": return self._send(200, session.gm_view())
                if path == "/api/observer/ari": return self._send(200, session.observer_view(session.ari.native_being_id))
                if path == "/api/observer/bex": return self._send(200, session.observer_view(session.bex.native_being_id))
                return self._send(404, {"error": "unknown Arena endpoint"})
            except Exception as exc:
                message = ("Arena request failed; no session data was returned."
                           if isinstance(session, GeneratedArenaSession) else str(exc))
                return self._send(500, {"error": message})
        def do_POST(self):
            path = urlsplit(self.path).path
            generated = isinstance(session, GeneratedArenaSession)
            actions = {
                "/api/generated/generate": "generate",
                "/api/generated/encounter-name": "rename_encounter",
                "/api/generated/player-name": "rename_player",
                "/api/generated/destination": "destination",
                "/api/generated/stop": "stop",
                "/api/generated/run": "run",
                "/api/generated/advance": "advance",
                "/api/generated/inspect": "inspect",
                "/api/generated/pickup": "pickup",
                "/api/generated/ready-weapon": "ready_weapon",
                "/api/generated/rename-entity": "rename_entity",
            }
            action = actions.get(path, "unknown")
            request_id, client_sequence = ((None, None) if not generated or action == "unknown"
                else session.begin_trace_request(action,
                    self.headers.get("X-Arena-Client-Seq")))
            def finish(status, body, *, classification=None, detail=None):
                if generated and action != "unknown":
                    session.finish_trace_request(request_id, client_sequence, action,
                        "accepted" if status < 400 else "refused", status,
                        classification=classification, detail=detail)
                return self._send(status, body)
            def refusal_class(exc, default):
                cause = getattr(exc, "__cause__", None)
                return type(cause).__name__ if cause is not None else default
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 1024:
                    raise ArenaRequestError("request body length is outside the accepted range")
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ArenaRequestError("request body must be valid UTF-8 JSON") from exc
                if type(payload) is not dict:
                    raise ArenaRequestError("request body must be a JSON object")
                if isinstance(session, GeneratedArenaSession):
                    if path == "/api/generated/trace":
                        if not session.trace_ui_enabled:
                            return self._send(404, {"error": "unknown generated Arena endpoint"})
                        origin = self.headers.get("Origin")
                        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
                        if origin is not None and origin != expected_origin:
                            return self._send(404, {"error": "unknown generated Arena endpoint"})
                        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                            return self._send(415, {"error": "trace events require JSON"})
                        try:
                            return self._send(200, session.accept_client_trace(payload))
                        except ValueError as exc:
                            return self._send(409, {"error": str(exc)})
                    routes = {
                        "/api/generated/generate": session.generate,
                        "/api/generated/encounter-name": session.rename_encounter,
                        "/api/generated/player-name": session.rename_player,
                        "/api/generated/destination": session.choose_destination,
                        "/api/generated/stop": session.stop_movement,
                        "/api/generated/inspect": session.inspect_entity,
                        "/api/generated/pickup": session.choose_pickup,
                        "/api/generated/ready-weapon": session.choose_ready_weapon,
                        "/api/generated/rename-entity": session.rename_entity,
                    }
                    if path == "/api/generated/run":
                        if payload != {}: raise ArenaBrowserRequestError("Run accepts an empty request")
                        result = session.choose_run()
                        return finish(200, result)
                    if path == "/api/generated/advance":
                        if payload != {"seconds": 1}: raise ArenaBrowserRequestError("advance accepts exactly one second")
                        result = session.advance_one_second(
                            trace_request_id=request_id,
                            trace_client_sequence=client_sequence)
                        return finish(200, result)
                    operation = routes.get(path)
                    if operation is None:
                        return self._send(404, {"error": "unknown generated Arena endpoint"})
                    result = operation(payload)
                    detail = None
                    if action == "generate":
                        detail = (f"xp={int(payload['starting_experience'])} "
                                  f"map={int(payload['width_cells'])}x{int(payload['height_cells'])}")
                    elif action == "destination":
                        outcome = result.get("movement_outcome")
                        detail = (f"cell=({payload['column']},{payload['row']}) "
                                  f"rate={payload['rate']} policy={payload['facing_policy']} "
                                  f"plan={'accepted' if result.get('movement_plan') else outcome}")
                    elif action in ("inspect", "pickup", "ready_weapon", "rename_entity"):
                        selected = result.get("selected_entity") or {}
                        detail = f"entity_type={selected.get('category', 'visible-entity')} type={selected.get('type', 'unknown')}"
                        if action == "pickup":
                            detail += " choice=accepted"
                        elif action == "ready_weapon":
                            detail = f"hand={payload.get('hand', 'unknown')} choice=accepted"
                        elif action == "rename_entity":
                            detail += " display_name_updated=true"
                    return finish(200, result, detail=detail)
                if path == "/api/spot":
                    if payload != {"operation": "ari_spots_bex"}:
                        raise ArenaRequestError("only the allowlisted Ari→Bex Spot operation is supported")
                    return self._send(200, session.submit_spot())
                if path == "/api/advance":
                    if payload != {"seconds": 1}:
                        raise ArenaRequestError("advance accepts exactly one second")
                    return self._send(200, session.advance_one_second())
                if path == "/api/save":
                    if payload != {}:
                        raise ArenaRequestError("save accepts an empty request; destination is host-configured")
                    if session.active is not None:
                        return self._send(200, session.save_s7_state())
                    return self._send(200, session.save_supported_state())
                if path == "/api/run":
                    if payload != {"operation": "ari_run_plus_x"}:
                        raise ArenaRequestError("only the allowlisted Ari Run +X operation is supported")
                    return self._send(200, session.submit_run())
                return self._send(404, {"error": "unknown Arena endpoint"})
            except ArenaRequestError as exc:
                if generated and action != "unknown":
                    return finish(409, {"error": str(exc)}, classification="request_validation")
                return self._send(409, {"error": str(exc)})
            except ArenaBrowserRequestError as exc:
                if generated and action != "unknown":
                    body = {"error": str(exc)}
                    if exc.movement_refusal is not None:
                        body["movement_refusal"] = dict(exc.movement_refusal)
                    classification = ("native_movement_refusal" if exc.movement_refusal is not None
                                      else refusal_class(exc, "arena_request_refused"))
                    return finish(409, body, classification=classification)
                return self._send(409, {"error": str(exc)})
            except ChoiceRejected as exc:
                if generated and action != "unknown":
                    return finish(409, {"error": str(exc)}, classification="choice_rejected")
                return self._send(409, {"error": str(exc)})
            except (TypeError, ValueError) as exc:
                if generated and action != "unknown":
                    return finish(409, {"error": str(exc)}, classification="native_validation")
                return self._send(409, {"error": str(exc)})
            except Exception as exc:
                message = ("Arena request failed; no session data was returned."
                           if isinstance(session, GeneratedArenaSession) else str(exc))
                if generated and action != "unknown":
                    return finish(500, {"error": message},
                                  classification=type(exc).__name__)
                return self._send(500, {"error": message})
        def log_message(self, fmt, *args):
            return
    return Handler
def serve_local(port=8000, *, session=None):
    """Serve only on IPv4 loopback; the host is intentionally not configurable."""
    session = session or ArenaSession()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(session))
    print(f"Universe Encounter Arena: http://127.0.0.1:{server.server_port}/", flush=True)
    if isinstance(session, GeneratedArenaSession):
        print("Generated Arena shell; player projection only, no client-selected IDs. Ctrl-C to stop.", flush=True)
    else:
        print("Local GM/developer tool; no client-selected path or Action IDs. Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
