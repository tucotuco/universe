#!/usr/bin/env python3
"""Drainage-constrained terrain visualization. No third-party dependencies.

    python examples/terrain_from_watershed.py --open
    python examples/terrain_from_watershed.py --watershed some-watershed-world.json --open
    python examples/terrain_from_watershed.py --load terrain-world.json --open
"""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import RLock
import webbrowser

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from geographical_watershed import WatershedDesign
from geographical_drainage_terrain import DrainageTerrainDesign

HERE=Path(__file__).resolve().parent
TEMPLATE=HERE/'terrain_from_watershed_template.html'


def sample_world():
    watershed=WatershedDesign(seed=845)
    for branch,index in (('main',2),('north',4),('south',7)):
        watershed.commit(watershed.preview(branch,index))
    return DrainageTerrainDesign(watershed)


class DrainageTerrainApp:
    def __init__(self,world):
        self.world=world
        self.pending=None
        self.lock=RLock()

    def invoke(self,route,data):
        with self.lock:
            if route=='/api/inspect':
                return self.world.inspect(data['x_km'],data['y_km'])
            if route=='/api/preview':
                self.pending=self.world.preview(data['tile'],data.get('candidate_index',0))
                return {'proposal':self.pending.as_dict(),'mesh':self.world.mesh(proposal=self.pending)}
            if route=='/api/commit':
                if self.pending is None:
                    raise ValueError('Preview terrain before committing')
                result=self.world.commit(self.pending)
                self.pending=None
                return {'committed':result,'mesh':self.world.mesh(), 'state':self.world.state()}
            if route=='/api/condition':
                condition=self.world.add_condition(data)
                self.pending=None
                return {'condition':condition,'state':self.world.state()}
            if route=='/api/mesh':
                return self.world.mesh()
            if route=='/api/drainage':
                return self.world.downhill_witness(data['x_km'],data['y_km'],self.pending)
            raise ValueError('Unknown operation')


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def json_reply(self,payload,status=200):
            encoded=json.dumps(payload,allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        def do_GET(self):
            if self.path=='/':
                data=TEMPLATE.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif self.path=='/api/state':
                with app.lock:
                    self.json_reply(app.world.state())
            elif self.path=='/api/mesh':
                with app.lock:
                    self.json_reply(app.world.mesh())
            else:
                self.send_error(404)
        def do_POST(self):
            origin=self.headers.get('Origin')
            host=self.headers.get('Host','')
            if origin and origin!='http://'+host:
                self.json_reply({'error':'Cross-origin commands are not accepted'},403)
                return
            try:
                if self.path not in ('/api/inspect','/api/preview','/api/commit',
                                     '/api/condition','/api/mesh','/api/drainage'):
                    self.json_reply({'error':'Unknown operation'},404)
                    return
                length=int(self.headers.get('Content-Length','0'))
                if length<0 or length>20000:
                    raise ValueError('Invalid request length')
                payload=json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(payload,dict):
                    raise ValueError('Expected an object')
                self.json_reply(app.invoke(self.path,payload))
            except (ValueError,TypeError,KeyError,OverflowError) as exc:
                self.json_reply({'error':str(exc)},400)
        def log_message(self,*args):
            pass
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watershed',type=Path,help='Existing committed watershed export')
    parser.add_argument('--load',type=Path,help='Existing committed terrain export')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    if args.load and args.watershed:
        parser.error('--load and --watershed are mutually exclusive')
    if args.load:
        world=DrainageTerrainDesign.loads(args.load.read_text(encoding='utf-8'))
    elif args.watershed:
        world=DrainageTerrainDesign(WatershedDesign.loads(args.watershed.read_text(encoding='utf-8')))
    else:
        world=sample_world()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(DrainageTerrainApp(world)))
    url=f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'Drainage-constrained terrain designer: {url}\nCtrl-C to stop.',flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=='__main__':
    main()
