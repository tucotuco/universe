"""Loopback-only presentation adapter for the bounded native Encounter Arena."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import RLock
from urllib.parse import urlsplit

from activities import SpotAction
from action_choice import ChoiceRejected
from examples.npc_encounter_arena import build_unstarted_arena


class ArenaRequestError(ValueError):
    """Request is outside the allowlisted Arena operations."""


class ArenaSession:
    """One in-memory native transactional Arena; Universe remains authoritative."""

    def __init__(self, *, die_roll=20):
        self.scenario = build_unstarted_arena(die_roll=die_roll)
        self.encounter = self.scenario["encounter"]
        self.world = self.encounter.universe
        self.ari, self.bex = self.scenario["candidate_bindings"]
        self.die_roll = die_roll
        self._rng_initial = self.scenario["rng"].state
        self._spot = None
        self._choice = None
        self._lock = RLock()

    def _inspection(self):
        if self.encounter.time < 1:
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
                    "native_definition": binding.native_definition_name,
                    "source_sha256": binding.source_sha256,
                })
            choice = None
            committed_action = None
            if self._choice is not None:
                choice = self.encounter.get_choice(self._choice.id)
                if inspection is not None and self._spot.id in inspection.actions:
                    result = inspection.action(self._spot.id)
                    facts = dict(result.facts.metadata)
                    committed_action = {
                        "id": self._spot.id, "boundary": result.resolved_boundary,
                        "outcome": result.facts.outcome, "roll": facts.get("roll"),
                        "effective_dc": facts.get("effective_dc"),
                        "effect_ids": [str(effect.identity) for effect in result.effects],
                    }
            timeline = [] if inspection is None else [
                {"boundary": row.boundary, "start": row.start,
                 "action_ids": list(row.action_ids)} for row in inspection.timeline]
            return {
                "audience": "GM/developer omniscient Reality view; local operator tool, not an auth boundary",
                "time": self.encounter.time, "encounter_id": self.encounter.id,
                "participants": participants,
                "choice": None if choice is None else {
                    "id": choice.id, "state": choice.state,
                    "action_ids": list(choice.action_ids), "first_start": choice.first_start},
                "spot": committed_action, "committed_timeline": timeline,
                "rng_unchanged": self.scenario["rng"].state == self._rng_initial,
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
            draft = self.encounter.propose_choice({"spot-ari-bex": action})
            validation = self.encounter.validate_choice(draft)
            if not validation.valid:
                raise ChoiceRejected(validation.diagnostics)
            choice = self.encounter.accept_valid_choice(validation)
            self._spot, self._choice = action, choice
            return {"choice_id": choice.id, "state": choice.state,
                    "action_ids": list(choice.action_ids)}

    def advance_one_second(self):
        with self._lock:
            if self.encounter.time >= 6:
                raise ArenaRequestError("this bounded Arena ends at boundary 6")
            before = self.encounter.time
            self.encounter.step(1)
            if self.encounter.time != before + 1:
                raise RuntimeError("native Encounter did not advance exactly one second")
            return self.gm_view()


_PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Universe Encounter Arena</title><style>
body{font:16px system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#202533}.tag{background:#f1e8d3;padding:.65rem;border-left:4px solid #a87520}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}section{border:1px solid #ccd2da;border-radius:8px;padding:1rem}button{padding:.6rem 1rem;margin:.4rem .4rem .4rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f7f8;padding:.8rem}svg{width:100%;height:230px;background:#f5f8fb;border:1px solid #d3dae2}
</style><h1>Universe Encounter Arena</h1><p class="tag"><b>Local GM/developer tool.</b> The GM panel is omniscient Reality inspection. Ari and Bex panels are separate observer Awareness projections. This localhost page is not an authentication boundary.</p>
<section><h2>GM / developer Reality view</h2><p id="clock"></p><svg viewBox="0 0 520 220" role="img" aria-label="Cartesian Arena map"><line x1="30" y1="180" x2="500" y2="180" stroke="#667"/><line x1="30" y1="20" x2="30" y2="180" stroke="#667"/><g id="markers"></g></svg><pre id="participants"></pre><p>Supported operation: Ari Spots Bex (GM-directed target; fixed scenario roll). Submit before stepping, then advance one second per click. The six-second Action commits at boundary 6.</p><button id="spot">Submit Ari → Bex Spot Choice</button><button id="advance">Advance one second</button><p id="message" role="status"></p><h3>Choice and committed result</h3><pre id="choice"></pre><h3>Committed boundary timeline</h3><pre id="timeline"></pre></section>
<div class="grid"><section><h2>Ari observer projection</h2><pre id="ari"></pre></section><section><h2>Bex observer projection</h2><pre id="bex"></pre></section></div>
<script>
async function req(path,method='GET',body){const o={method,headers:{}};if(body!==undefined){o.headers['Content-Type']='application/json';o.body=JSON.stringify(body)}const r=await fetch(path,o),d=await r.json();if(!r.ok)throw Error(d.error||('HTTP '+r.status));return d}
function show(id,v){document.getElementById(id).textContent=JSON.stringify(v,null,2)}
function draw(rows){const g=document.getElementById('markers');while(g.firstChild)g.removeChild(g.firstChild);for(const p of rows){const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',String(50+Number(p.position.x)*100));c.setAttribute('cy',String(170-Number(p.position.y)*100));c.setAttribute('r','8');c.setAttribute('fill',p.name==='Ari'?'#316ab0':'#bd573d');g.appendChild(c);const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',String(62+Number(p.position.x)*100));t.setAttribute('y',String(174-Number(p.position.y)*100));t.textContent=p.name;g.appendChild(t)}}
async function refresh(){const g=await req('/api/gm');document.getElementById('clock').textContent='Encounter time: '+g.time+' s';draw(g.participants);show('participants',g.participants);show('choice',{choice:g.choice,committed_action:g.spot});show('timeline',g.committed_timeline);show('ari',await req('/api/observer/ari'));show('bex',await req('/api/observer/bex'));document.getElementById('spot').disabled=!!g.choice||g.time!==0;document.getElementById('advance').disabled=g.time>=6}
document.getElementById('spot').onclick=async()=>{try{await req('/api/spot','POST',{operation:'ari_spots_bex'});document.getElementById('message').textContent='Choice accepted by native Encounter ChoiceBook.';await refresh()}catch(e){document.getElementById('message').textContent=e.message}};
document.getElementById('advance').onclick=async()=>{try{await req('/api/advance','POST',{seconds:1});document.getElementById('message').textContent='Advanced one native Encounter second.';await refresh()}catch(e){document.getElementById('message').textContent=e.message}};refresh().catch(e=>document.getElementById('message').textContent=e.message);
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


def serve_local(port=8000):
    """Serve only on IPv4 loopback; the host is intentionally not configurable."""
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(ArenaSession()))
    print(f"Universe Encounter Arena: http://127.0.0.1:{server.server_port}/")
    print("Local GM/developer tool; in-memory only, not a save or login boundary. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
