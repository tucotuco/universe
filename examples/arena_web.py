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
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            try:
                if path == "/": return self._send(200, _PAGE, "text/html; charset=utf-8")
                if path == "/api/gm": return self._send(200, session.gm_view())
                if path == "/api/observer/ari": return self._send(200, session.observer_view(session.ari.native_being_id))
                if path == "/api/observer/bex": return self._send(200, session.observer_view(session.bex.native_being_id))
                return self._send(404, {"error": "unknown Arena endpoint"})
            except Exception as exc:
                return self._send(500, {"error": str(exc)})

        def do_POST(self):
            path = urlsplit(self.path).path
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
                return self._send(409, {"error": str(exc)})
            except ChoiceRejected as exc:
                return self._send(409, {"error": str(exc)})
            except (TypeError, ValueError) as exc:
                return self._send(409, {"error": str(exc)})
            except Exception as exc:
                return self._send(500, {"error": str(exc)})

        def log_message(self, fmt, *args):
            return
    return Handler


def serve_local(port=8000, *, session=None):
    """Serve only on IPv4 loopback; the host is intentionally not configurable."""
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(session or ArenaSession()))
    print(f"Universe Encounter Arena: http://127.0.0.1:{server.server_port}/", flush=True)
    print("Local GM/developer tool; no client-selected path or Action IDs. Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
