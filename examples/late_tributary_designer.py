#!/usr/bin/env python3
"""Explore a late tributary against partially committed drainage terrain.

    python examples/late_tributary_designer.py --open
    python examples/late_tributary_designer.py --terrain saved-terrain.json --open
    python examples/late_tributary_designer.py --load saved-extension.json --open
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import RLock
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from geographical_watershed import WatershedDesign
from geographical_drainage_terrain import DrainageTerrainDesign
from geographical_late_tributary import LateTributaryDesign

TEMPLATE = Path(__file__).with_name('late_tributary_designer_template.html')


def sample_world():
    watershed = WatershedDesign(seed=845)
    for branch, index in (('main', 2), ('north', 4), ('south', 7)):
        watershed.commit(watershed.preview(branch, index))
    terrain = DrainageTerrainDesign(watershed)
    for tile in ((1, 0), (2, 1)):
        terrain.commit(terrain.preview(tile, 3))
    return LateTributaryDesign(terrain)


class TributaryApp:
    def __init__(self, world):
        self.world = world
        self.pending = None
        self.lock = RLock()

    def invoke(self, path, data):
        with self.lock:
            if path == '/api/inspect':
                return self.world.inspect(data['x_km'], data['y_km'])
            if path == '/api/preview':
                self.pending = self.world.preview(data['x_km'], data['y_km'],
                                                  data.get('candidate_index', 0),
                                                  target=data.get('target', 'original'))
                return {'proposal': self.pending.as_dict(),
                        'mesh': self.world.mesh(proposal=self.pending),
                        'graph': self.world.graph(self.pending)}
            if path == '/api/commit':
                if self.pending is None:
                    raise ValueError('Preview a tributary before committing it')
                # The browser supplies its currently selected trial. Do not
                # commit a preview for a *different* target/source after an
                # intervening UI edit. Older callers may omit these fields.
                if ('target' in data and data['target'] !=
                        self.world._target_selector(self.pending.target_branch)):
                    raise ValueError('Confluence target changed; preview again')
                if ('candidate_index' in data and
                        data['candidate_index'] != self.pending.candidate_index):
                    raise ValueError('Candidate index changed; preview again')
                if 'x_km' in data or 'y_km' in data:
                    coords = self.world.terrain._coords(
                        data.get('x_km', self.pending.source[0]),
                        data.get('y_km', self.pending.source[1]))
                    if tuple(round(x, 6) for x in coords) != self.pending.source:
                        raise ValueError('Tributary source changed; preview again')
                committed = self.world.commit(self.pending)
                self.pending = None
                return {'committed': committed, 'state': self.world.state(),
                        'mesh': self.world.mesh(), 'graph': self.world.graph()}
            if path == '/api/reset':
                self.pending = None
                return {'mesh': self.world.mesh()}
            raise ValueError('Unknown operation')


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _respond(self, code, payload, mime='application/json'):
            data = (payload.encode('utf-8') if isinstance(payload, str)
                    else json.dumps(payload, allow_nan=False).encode('utf-8'))
            self.send_response(code)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                with app.lock:
                    if self.path in ('/', '/index.html'):
                        return self._respond(200, TEMPLATE.read_text(encoding='utf-8'), 'text/html')
                    if self.path == '/api/state':
                        return self._respond(200, app.world.state())
                    if self.path == '/api/mesh':
                        return self._respond(200, app.world.mesh())
                self._respond(404, {'error': 'Unknown path'})
            except (ValueError, KeyError) as error:
                self._respond(400, {'error': str(error)})

        def do_POST(self):
            origin = self.headers.get('Origin')
            expected = f'http://{self.headers.get("Host")}'
            if origin and origin != expected:
                return self._respond(403, {'error': 'Cross-origin commands forbidden'})
            try:
                size = int(self.headers.get('Content-Length', 0))
                if size < 0 or size > 16384:
                    raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object')
                self._respond(200, app.invoke(self.path, data))
            except (ValueError, KeyError, TypeError) as error:
                self._respond(400, {'error': str(error)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain', type=Path, help='Load an established drainage-terrain world')
    parser.add_argument('--load', type=Path, help='Reload an exported late-tributary world')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if args.load and args.terrain:
        parser.error('Use only one of --load and --terrain')
    if args.load:
        world = LateTributaryDesign.loads(args.load.read_text(encoding='utf-8'))
    elif args.terrain:
        world = LateTributaryDesign(DrainageTerrainDesign.loads(args.terrain.read_text(encoding='utf-8')))
    else:
        world = sample_world()
    with ThreadingHTTPServer((args.host, args.port), make_handler(TributaryApp(world))) as server:
        url = f'http://{args.host}:{server.server_port}/'
        print(f'Late-tributary designer: {url} (Ctrl-C to stop)', flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
