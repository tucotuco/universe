#!/usr/bin/env python3
"""A local, demand-driven terrain designer. Standard library only.

Launch from the project root with:
    python examples/geographical_designer.py --open
Use --load FILE to reopen a committed world exported from the browser.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import RLock
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from geographical_requirements import GeographicalDesign

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / 'geographical_designer_template.html'
DEFAULT = HERE / 'geographical_region.json'


class GeographyApp:
    def __init__(self, design):
        self.design = design
        self.pending = None
        self.lock = RLock()

    def invoke(self, route, data):
        with self.lock:
            if route == '/api/inspect':
                return self.design.inspect(data['x_km'], data['y_km'])
            if route == '/api/preview':
                self.pending = self.design.preview(
                    data['tile'], data.get('candidate_index', 0), data.get('amplitude_m'))
                return {'proposal': self.pending.as_dict(),
                        'map': self.design.map_data(self.pending)}
            if route == '/api/commit':
                if self.pending is None:
                    raise ValueError('Preview a geographical refinement before committing')
                record = self.design.commit(self.pending)
                self.pending = None
                return {'committed': record, 'world': self.design.state(),
                        'map': self.design.map_data()}
            if route == '/api/condition':
                c = self.design.add_condition(data)
                self.pending = None
                return {'condition': c, 'world': self.design.state(),
                        'map': self.design.map_data()}
            if route == '/api/map':
                # Map requests without a pending preview show only established
                # relief plus the declared *approximate* coarse terrain.
                return self.design.map_data()
            raise ValueError('Unknown geographical operation')


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, obj, status=200):
            data = json.dumps(obj, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

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
                    self.send_json(app.design.state())
            else:
                self.send_error(404)

        def do_POST(self):
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            if origin and origin != 'http://' + host:
                self.send_json({'error': 'Cross-origin commands are not accepted'}, 403)
                return
            if self.path not in ('/api/inspect', '/api/preview', '/api/commit', '/api/condition', '/api/map'):
                self.send_json({'error': 'Unknown geographical operation'}, 404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 20_000:
                    raise ValueError('Invalid request length')
                body = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(body, dict):
                    raise ValueError('Expected a JSON object')
                self.send_json(app.invoke(self.path, body))
            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                self.send_json({'error': str(exc)}, 400)

        def log_message(self, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT)
    parser.add_argument('--load', type=Path, help='Exported geographical world JSON')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if args.load:
        design = GeographicalDesign.loads(args.load.read_text(encoding='utf-8'))
    else:
        design = GeographicalDesign(**json.loads(args.config.read_text(encoding='utf-8')))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(GeographyApp(design)))
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'Geographical designer: {url}\nCtrl-C to stop.', flush=True)
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
