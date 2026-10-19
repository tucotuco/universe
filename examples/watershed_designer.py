#!/usr/bin/env python3
"""Interactive constrained river-network realization; standard library only.

    python examples/watershed_designer.py --open
    python examples/watershed_designer.py --load universe-watershed-world.json --open
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import RLock
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from geographical_watershed import WatershedDesign

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE/'watershed_designer_template.html'
DEFAULT = HERE/'watershed_region.json'


class WatershedApp:
    def __init__(self, world):
        self.world = world
        self.pending = None
        self.lock = RLock()

    def invoke(self, route, data):
        with self.lock:
            if route == '/api/inspect':
                return self.world.inspect(data.get('question', 'river_to_bay'))
            if route == '/api/preview':
                self.pending = self.world.preview(data.get('branch', 'main'),
                                                  data.get('candidate_index', 0))
                return {'proposal': self.pending.as_dict(),
                        'network': self.world.network(self.pending)}
            if route == '/api/commit':
                if self.pending is None:
                    raise ValueError('Preview a river course before committing')
                record = self.world.commit(self.pending)
                self.pending = None
                return {'committed': record, 'world': self.world.state(),
                        'network': self.world.network()}
            if route == '/api/condition':
                value = self.world.add_condition(data)
                self.pending = None
                return {'condition': value, 'world': self.world.state(),
                        'network': self.world.network()}
            if route == '/api/network':
                return self.world.network()
            raise ValueError('Unknown watershed operation')


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, obj, status=200):
            encoded = json.dumps(obj, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if self.path == '/':
                html = TEMPLATE.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif self.path == '/api/state':
                with app.lock:
                    self.send_json(app.world.state())
            else:
                self.send_error(404)

        def do_POST(self):
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            if origin and origin != 'http://' + host:
                self.send_json({'error': 'Cross-origin commands are not accepted'}, 403)
                return
            if self.path not in ('/api/inspect','/api/preview','/api/commit',
                                 '/api/condition','/api/network'):
                self.send_json({'error':'Unknown watershed operation'}, 404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 20000:
                    raise ValueError('Invalid request length')
                payload = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('Expected a JSON mapping')
                self.send_json(app.invoke(self.path, payload))
            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                self.send_json({'error': str(exc)}, 400)

        def log_message(self, *_args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT)
    parser.add_argument('--load', type=Path)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    world = (WatershedDesign.loads(args.load.read_text(encoding='utf-8')) if args.load else
             WatershedDesign(**json.loads(args.config.read_text(encoding='utf-8'))))
    server = ThreadingHTTPServer(('127.0.0.1',args.port), make_handler(WatershedApp(world)))
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'Watershed designer: {url}\nCtrl-C to stop.', flush=True)
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
