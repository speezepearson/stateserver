import argparse
from pathlib import Path

from aiohttp import web

from . import make_routes

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--state-dir', type=Path, default=Path.cwd())
parser.add_argument('-p', '--port', type=int, default=48402)
args = parser.parse_args()

app = web.Application()
app.add_routes(make_routes(state_dir=args.state_dir))
web.run_app(app, port=args.port)
