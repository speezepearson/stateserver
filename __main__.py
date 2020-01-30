import argparse
from pathlib import Path

from aiohttp import web

from . import make_routes, _unsafe_allow_all_origins

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--state-dir', type=Path, default=Path.cwd())
parser.add_argument('-p', '--port', type=int, default=48402)
parser.add_argument('--unsafe', action='store_true')

def main(
    state_dir: Path,
    port: int,
    unsafe: bool,
):

    app = web.Application(middlewares=[_unsafe_allow_all_origins] if unsafe else [])
    app.add_routes(make_routes(state_dir=state_dir, unsafe=unsafe))
    web.run_app(app, port=port)

if __name__ == '__main__':
    args = parser.parse_args()
    main(
        state_dir=args.state_dir,
        port=args.port,
        unsafe=args.unsafe,
    )
