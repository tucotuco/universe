"""Player-controlled one-on-one Universe combat in a local browser.

Run from the repository root: python examples/live_combat.py --open
Stop the localhost server using Ctrl-C. No internet or extra dependencies.
"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from tactical_duel import TacticalDuel


def make_handler(game, audit=False, *, save_path=None, replay_only=False):
    """Local-only HTTP interface. The browser receives a filtered view by default."""
    template = (ROOT / 'examples' / 'live_combat_template.html').read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, content, kind):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; style-src 'unsafe-inline'; "
                             "script-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(content)

        def json_response(self, code, data):
            self.respond(code, json.dumps(data, ensure_ascii=True).encode('utf-8'),
                         'application/json; charset=utf-8')

        def trusted_host(self):
            return self.headers.get('Host') == ('127.0.0.1:' + str(self.server.server_port))

        def do_GET(self):
            if not self.trusted_host():
                return self.json_response(403, {'error': 'Host rejected.'})
            if self.path == '/':
                self.respond(200, template, 'text/html; charset=utf-8')
            elif self.path == '/state':
                state = game.state(audit=audit)
                state['replay_only'] = replay_only
                self.json_response(200, state)
            elif self.path == '/timeline':
                self.json_response(200, {'frames': game.timeline(audit=audit)})
            else:
                self.json_response(404, {'error': 'Unknown resource.'})

        def do_POST(self):
            if not self.trusted_host():
                return self.json_response(403, {'error': 'Host rejected.'})
            if self.path not in ('/choose', '/save'):
                return self.json_response(404, {'error': 'Unknown resource.'})
            # No CORS, JSON-only, bound to loopback. Require a browser Origin
            # matching this exact local service to prevent remote drive-by posts.
            origin = self.headers.get('Origin')
            expected = 'http://127.0.0.1:' + str(self.server.server_port)
            if origin != expected:
                return self.json_response(403, {'error': 'Origin rejected.'})
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                return self.json_response(415, {'error': 'JSON required.'})
            try:
                length = int(self.headers.get('Content-Length', '-1'))
                if not 0 < length <= 256:
                    raise ValueError('Invalid request size.')
                body = json.loads(self.rfile.read(length).decode('utf-8'))
                if self.path == '/save':
                    if replay_only:
                        raise ValueError('Replay is read-only.')
                    if body != {}:
                        raise ValueError('Save takes an empty JSON object.')
                    if save_path is None:
                        raise ValueError('Saving is not configured.')
                    payload = game.to_session()
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = save_path.with_name(save_path.name + '.tmp')
                    try:
                        with temporary.open('w', encoding='utf-8') as stream:
                            json.dump(payload, stream, indent=2)
                            stream.write('\n')
                        os.replace(temporary, save_path)
                    finally:
                        if temporary.exists():
                            temporary.unlink()
                    result = {'saved': str(save_path), 'time': game.encounter.time}
                else:
                    if replay_only:
                        raise ValueError('Replay is read-only.')
                    if not isinstance(body, dict) or not isinstance(body.get('command'), str) or (
                            set(body) not in ({'command'}, {'command', 'effort'})):
                        raise ValueError('Expected command with optional effort allocation.')
                    result = game.choose(body['command'], body.get('effort'))
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
                return self.json_response(400, {'error': str(exc)})
            self.json_response(200, result if self.path == '/save' or not audit else game.state(audit=True))

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--port', type=int, default=0, help='local port; 0 selects a free port')
    parser.add_argument('--audit', action='store_true', help='developer-only full opponent state')
    parser.add_argument('--open', action='store_true', help='open browser automatically')
    parser.add_argument('--save', type=Path,
                        help='local save path; defaults to loaded file or workspace/combat-session.json')
    parser.add_argument('--load', type=Path, help='load a saved encounter and continue')
    parser.add_argument('--replay', type=Path, help='load a saved encounter for read-only review')
    args = parser.parse_args(argv)
    if args.load is not None and args.replay is not None:
        parser.error('--load and --replay are mutually exclusive')
    source = args.load or args.replay
    if source is not None:
        with source.open('r', encoding='utf-8') as stream:
            game = TacticalDuel.from_session(json.load(stream))
    else:
        game = TacticalDuel(seed=args.seed)
    save_path = (args.save or args.load or ROOT / 'workspace' / 'combat-session.json').expanduser().resolve()
    with HTTPServer(('127.0.0.1', args.port), make_handler(
            game, args.audit, save_path=save_path, replay_only=args.replay is not None)) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print('Universe live combat:', url, flush=True)
        if args.audit:
            print('DEVELOPER AUDIT: objective opponent data exposed.', flush=True)
        print('Save target:', save_path, flush=True)
        if args.replay is not None:
            print('Read-only replay session.', flush=True)
        print('Press Ctrl-C to stop.', flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return game


if __name__ == '__main__':
    main()
