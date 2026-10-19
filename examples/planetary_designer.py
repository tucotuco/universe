#!/usr/bin/env python3
"""Local interactive planetary demand designer (standard library only).

Run ``python examples/planetary_designer.py --open`` from the repository root.
Previewing candidates does not commit; a Commit click is explicit. Export the
versioned JSON design to preserve decisions, and reload with --load FILE.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import RLock
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from planetary_requirements import PlanetaryDesign

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / 'planetary_designer_template.html'
DEFAULT = HERE / 'planetary_design_conditions.json'


class DesignerApp:
    def __init__(self, design):
        self.design = design
        self.pending = None
        self.lock = RLock()

    def invoke(self, route, data):
        with self.lock:
            if route == '/api/inspect':
                return self.design.inspect(data.get('query', 'time_to_sunset_hours'),
                                           data.get('latitude_deg', 40), data.get('time_s', 0))
            if route == '/api/preview':
                proposal = self.design.preview(query=data.get('query', 'time_to_sunset_hours'),
                                               latitude_deg=data.get('latitude_deg', 40),
                                               time_s=data.get('time_s', 0),
                                               trial=data.get('trial', {}),
                                               candidate_index=data.get('candidate_index', 0))
                self.pending = proposal
                return proposal.as_dict()
            if route == '/api/commit':
                if self.pending is None:
                    raise ValueError('Preview a candidate before committing')
                changes = self.design.commit(self.pending)
                self.pending = None
                return {'committed': changes, 'world': self.design.export()}
            if route == '/api/condition':
                self.design.add_condition(data)
                self.pending = None
                return {'world': self.design.export()}
            raise ValueError('Unknown designer operation')


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, obj, code=200):
            payload = json.dumps(obj, allow_nan=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == '/':
                page = TEMPLATE.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(page)))
                self.end_headers()
                self.wfile.write(page)
            elif self.path == '/api/state':
                with app.lock:
                    self.send_json(app.design.export())
            else:
                self.send_error(404)

        def do_POST(self):
            origin = self.headers.get('Origin')
            expected = 'http://' + self.headers.get('Host', '')
            if origin and origin != expected:
                self.send_json({'error': 'Cross-origin commands are not accepted'}, 403)
                return
            if self.path not in ('/api/inspect', '/api/preview', '/api/commit', '/api/condition'):
                self.send_json({'error': 'Unknown operation'}, 404)
                return
            try:
                n = int(self.headers.get('Content-Length', '0'))
                if n < 0 or n > 20000:
                    raise ValueError('Invalid request length')
                raw = json.loads(self.rfile.read(n).decode('utf-8'))
                if not isinstance(raw, dict):
                    raise ValueError('Expected a JSON object')
                self.send_json(app.invoke(self.path, raw))
            except (ValueError, KeyError, TypeError) as exc:
                self.send_json({'error': str(exc)}, 400)

        def log_message(self, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--load', type=Path, help='Previously exported world design JSON')
    parser.add_argument('--config', type=Path, default=DEFAULT, help='Initial incomplete world and conditions')
    parser.add_argument('--open', action='store_true', help='Open the designer in a browser')
    parser.add_argument('--port', type=int, default=0, help='Loopback port; 0 selects an available port')
    args = parser.parse_args()
    if args.load:
        design = PlanetaryDesign.restore(json.loads(args.load.read_text(encoding='utf-8')))
    else:
        cfg = json.loads(args.config.read_text(encoding='utf-8'))
        design = PlanetaryDesign(**cfg)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(DesignerApp(design)))
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'Planetary designer: {url}\nCtrl-C to stop. Export JSON in the browser to save world commitments.', flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
