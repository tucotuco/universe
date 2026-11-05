"""Opt-in loopback browser for one native thrust by the external NPC fixture.

Run from the repository root with ``python examples/npc_being_arena_web.py``.
This is a local omniscient developer tool, not a player UI or auth boundary.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import threading
from urllib.parse import urlsplit

from npc_being_arena import build_arena


_PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>NPC Being Arena</title>
<style>
body{font:16px system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#17212b}
.banner{padding:1rem;background:#fff4d6;border:1px solid #e1c273;border-radius:.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem;margin:1rem 0}
section{border:1px solid #ccd4dc;border-radius:.5rem;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}
button{font:inherit;padding:.6rem 1rem;margin:.3rem .4rem .3rem 0}#state{background:#f3f6f8;padding:1rem;border-radius:.5rem}
</style>
<h1>External NPC → Native Being Arena</h1>
<p class="banner"><b>Local developer-only GM inspection.</b> This is omniscient scenario setup, not an Agent observation or authentication boundary. No observer endpoint is exposed. The fixture's full source record and unsupported fields are not sent to the browser.</p>
<div class="grid">
 <section><h2>Source-derived NPC</h2><pre id="source">Loading…</pre></section>
 <section><h2>Arena-authored mechanics</h2><pre id="arena">Loading…</pre></section>
</div>
<section><h2>Encounter progression</h2>
 <p>One fixed native Dagger thrust. Submit the Choice, inspect the pre-commit state, then advance to the scheduled boundary 4. Tobe's source-generated initial HP is mapped from <code>state.hps</code> to native initial/current HP; it is not a maximum-HP or Hit Dice mapping. Race, age, class/level/XP and possessions are not imported. The source <code>armed combat</code> rank is imported, but this implementation does not calculate the full revision-60 strategy pool.</p>
 <button id="submit">Submit fixed Dagger thrust</button>
 <button id="advance" disabled>Advance to native commit boundary</button>
 <pre id="state">Loading…</pre>
 <p>Native committed inspection does not expose the numerical d20 result. This page shows the native outcome, recorded metadata, Target HP and causal damage without reconstructing a roll. The opponent's HP is Arena-authored.</p>
</section>
<script>
async function request(path, method='GET', body){const opts={method,headers:{}};if(body!==undefined){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}const r=await fetch(path,opts);let d;try{d=await r.json()}catch{d={error:'Invalid server response'}}if(!r.ok)throw Error(d.error||('HTTP '+r.status));return d}
function display(id,value){document.getElementById(id).textContent=JSON.stringify(value,null,2)}
async function refresh(){const s=await request('/api/state');display('source',s.developer_view.source_derived);display('arena',{npc_native:s.developer_view.npc_native,opponent_arena_authored:s.developer_view.opponent_arena_authored,arena_authored:s.developer_view.arena_authored,fixture_sha256:s.developer_view.source_sha256});display('state',{time:s.time,progression_mode:s.progression_mode,choice:s.choice,precommit:s.precommit,committed_result:s.committed_result,native_receipt_boundaries:s.native_receipt_boundaries});document.getElementById('submit').disabled=s.submitted;document.getElementById('advance').disabled=!s.submitted||s.committed;}
document.getElementById('submit').onclick=async()=>{try{const a=await request('/api/submit','POST',{operation:'submit_fixed_thrust'});display('state',{accepted:a,precommit:true,note:'Choice accepted; no boundary has advanced and no result is available yet.'});await refresh()}catch(e){document.getElementById('state').textContent=e.message}};
document.getElementById('advance').onclick=async()=>{try{await request('/api/advance','POST',{operation:'advance_to_commit'});await refresh()}catch(e){document.getElementById('state').textContent=e.message}};
refresh().catch(e=>document.getElementById('state').textContent=e.message);
</script></html>"""


class ArenaRequestRejected(ValueError):
    pass


def _state(arena):
    choice = None
    if arena.choice is not None:
        choice = {"id": arena.choice.id, "state": arena.choice.state,
                  "action_ids": list(arena.choice.action_ids)}
    return {
        "developer_view": arena.developer_view(),
        "time": arena.encounter.time,
        "progression_mode": arena.encounter.progression_mode,
        "submitted": arena.submitted,
        "precommit": arena.submitted and arena.committed_result is None,
        "committed": arena.committed_result is not None,
        "choice": choice,
        "action": (None if not arena.submitted else {
            "id": arena.strike.id, "start_time": arena.strike.start_time,
            "scheduled_end_time": arena.strike.end_time,
        }),
        "committed_result": arena.committed_result,
        "native_receipt_boundaries": [
            row.boundary for row in arena.encounter.__dict__.get("_atomic_interval_history", ())],
    }


def make_handler(arena):
    """Create an allowlisted handler for one in-memory native Arena instance."""
    lock = threading.RLock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "UniverseNpcBeingArena/1"

        def _send(self, status, payload, content_type="application/json; charset=utf-8"):
            body = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    if content_type.startswith("application/json") else payload.encode("utf-8"))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                return self._send(200, _PAGE, "text/html; charset=utf-8")
            if path == "/api/state":
                with lock:
                    return self._send(200, _state(arena))
            return self._send(404, {"error": "unknown Arena endpoint"})

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in ("/api/submit", "/api/advance"):
                return self._send(404, {"error": "unknown Arena endpoint"})
            if self.headers.get_content_type() != "application/json":
                return self._send(415, {"error": "Content-Type must be application/json"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 1024:
                    raise ArenaRequestRejected("request body length is outside the accepted range")
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ArenaRequestRejected("request body must be valid UTF-8 JSON") from exc
                if type(payload) is not dict:
                    raise ArenaRequestRejected("request body must be a JSON object")
                if path == "/api/submit":
                    if payload != {"operation": "submit_fixed_thrust"}:
                        raise ArenaRequestRejected("only the fixed Arena thrust operation is supported")
                    with lock:
                        return self._send(200, arena.submit_thrust())
                if payload != {"operation": "advance_to_commit"}:
                    raise ArenaRequestRejected("advance accepts only the fixed commit operation")
                with lock:
                    return self._send(200, arena.advance_to_commit())
            except ArenaRequestRejected as exc:
                return self._send(400, {"error": str(exc)})
            except RuntimeError as exc:
                return self._send(409, {"error": str(exc)})
            except (TypeError, ValueError) as exc:
                return self._send(409, {"error": str(exc)})
            except Exception as exc:
                return self._send(500, {"error": str(exc)})

        def _unsupported(self):
            return self._send(405, {"error": "method is not supported"})

        do_PUT = _unsupported
        do_PATCH = _unsupported
        do_DELETE = _unsupported
        do_OPTIONS = _unsupported

        def log_message(self, fmt, *args):
            return

    return Handler


def serve_local(port=8001, *, host="127.0.0.1", arena=None):
    """Serve the opt-in developer Arena on IPv4 loopback only."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("host must be an IPv4 loopback address") from exc
    if address.version != 4 or not address.is_loopback:
        raise ValueError("NPC Being Arena may bind only to IPv4 loopback")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    server = ThreadingHTTPServer((str(address), port), make_handler(arena or build_arena()))
    print(f"NPC Being Arena: http://127.0.0.1:{server.server_port}/", flush=True)
    print("Local developer-only inspection; no player or authentication boundary. Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="One-action loopback NPC Being Arena")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    serve_local(args.port)


if __name__ == "__main__":
    main()
