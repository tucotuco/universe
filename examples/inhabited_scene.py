#!/usr/bin/env python3
"""Local interactive village-at-dusk prototype, standard library only.

From Universe repository root:
  python examples/inhabited_scene.py --open
  python examples/inhabited_scene.py --load universe-inhabited-scene.json --open
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import RLock
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from inhabited_scene import InhabitedScene

PAGE = Path(__file__).with_name('inhabited_scene_template.html')


class SceneApp:
    def __init__(self, scene=None):
        self.scene = scene or InhabitedScene()
        self.lock = RLock()

    def invoke(self, path, payload):
        with self.lock:
            if path == '/api/act':
                if not isinstance(payload, dict) or set(payload) != {'operation', 'args'} or not isinstance(payload['args'], dict):
                    raise ValueError('Expected operation and args')
                event = self.scene.act(payload['operation'], **payload['args'])
                return {'event': event, 'state': self.scene.state(), 'map': self.scene.map_data()}
            raise ValueError('Unknown scene operation')


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, payload, code=200, mime='application/json'):
            body = (payload.encode('utf-8') if isinstance(payload, str) else
                    json.dumps(payload, allow_nan=False).encode('utf-8'))
            self.send_response(code)
            self.send_header('Content-Type', f'{mime}; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                with app.lock:
                    if self.path in ('/', '/index.html'):
                        return self.reply(PAGE.read_text(encoding='utf-8'), mime='text/html')
                    if self.path == '/api/state':
                        return self.reply({'state': app.scene.inspect(),
                                           'map': app.scene.map_data()})
                    if self.path == '/api/lantern':
                        return self.reply(app.scene.lantern_inquiry.assess(
                            app.scene._map_xy(app.scene.actors['traveler'])))
                    if self.path == '/api/export':
                        return self.reply(app.scene.export())
                self.reply({'error': 'Not found'}, 404)
            except (ValueError, KeyError, TypeError) as error:
                self.reply({'error': str(error)}, 400)

        def do_POST(self):
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                return self.reply({'error': 'Cross-origin commands forbidden'}, 403)
            if self.path != '/api/act':
                return self.reply({'error': 'Not found'}, 404)
            try:
                n = int(self.headers.get('Content-Length', '-1'))
                if not 0 <= n <= 5000:
                    raise ValueError('Request body size outside limit')
                data = json.loads(self.rfile.read(n).decode('utf-8'))
                self.reply(app.invoke(self.path, data))
            except (ValueError, KeyError, TypeError, OverflowError) as error:
                self.reply({'error': str(error)}, 400)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--load', type=Path, help='Previously exported scene journal')
    parser.add_argument('--open', action='store_true', help='Open browser automatically')
    parser.add_argument('--port', type=int, default=0, help='Port, 0 for automatic selection')
    parser.add_argument('--terrain-candidate', type=int, default=2, help='World-builder relief alternative (2: clear, 11: blocked)')
    parser.add_argument('--lantern-unlit', action='store_true', help='World-builder choice: lantern is not lit')
    options = parser.parse_args()
    if options.load and (options.terrain_candidate != 2 or options.lantern_unlit):
        parser.error('Do not combine --load with new-world lantern/terrain choices')
    scene = (InhabitedScene.restore(json.loads(options.load.read_text(encoding='utf-8')))
             if options.load else InhabitedScene(terrain_candidate_index=options.terrain_candidate,
                                                lantern_lit=not options.lantern_unlit))
    with ThreadingHTTPServer(('127.0.0.1', options.port), handler_for(SceneApp(scene))) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'Inhabited scene: {url} — Ctrl-C to stop', flush=True)
        if options.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
