import argparse
import asyncio
import collections
import json
import pprint
from pathlib import Path
from typing import Mapping

from aiohttp import web

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', type=int, default=8002)
args = parser.parse_args()

routes = web.RouteTableDef()
conditions: Mapping[str, asyncio.Condition] = collections.defaultdict(asyncio.Condition)

def get_state_path(name: str) -> Path:
    if not name.isalnum():
        raise ValueError(f'non alphanumeric: {name!r}')
    return (Path('states')/name).with_suffix('.json')

def get_state(name: str):
    path = get_state_path(name)
    if path.is_file():
        return json.load(path.open())
    else:
        return None

routes.static(prefix='/static', path=Path.cwd()/'static', follow_symlinks=True)

@routes.route('GET', '/states/{name:[a-zA-Z0-9]{,32}}')
async def server_get_state(request: web.Request):
    name: str = request.match_info['name']
    print('GET /states/' + name)
    assert name.isalnum()
    async with conditions[name]:
        return web.json_response({"current_state": get_state(name)})

@routes.route('POST', '/poll/{name:[a-zA-Z0-9]{,32}}')
async def server_poll(request: web.Request):
    name: str = request.match_info['name']
    print('POST /poll/' + name)
    assert name.isalnum()

    old_state = (await request.json())['current_state']
    condition = conditions[name]
    async with condition:
        await condition.wait_for(lambda: get_state(name) != old_state)
        return web.json_response({"current_state": get_state(name)})

@routes.route('POST', '/states/{name:[a-zA-Z0-9]{,32}}')
async def server_post_state(request: web.Request):
    name: str = request.match_info['name']
    print('POST /states/' + name)
    assert name.isalnum()
    path = get_state_path(name)
    try:
        request_state = await request.json()
    except ValueError:
        return web.Response(body='syntactically invalid JSON request', status=400)
    if not (isinstance(request_state, dict) and set(request_state.keys()) == {'old', 'new'}):
        return web.Response(body='semantically invalid JSON request', status=400)
    request_old = request_state['old']
    request_new = request_state['new']

    async with conditions[name]:
        current = get_state(name)
        if current == request_old:
            print("transitioning:")
            pprint.pprint(request_state)
            path.write_text(json.dumps(request_new))
            conditions[name].notify_all()
            return web.json_response({"success": True, "current_state": request_new})
        else:
            print("not transitioning")
            pprint.pprint({"actual": current, "supposed": request_old, "desired": request_new})
            return web.json_response({"success": False, "current_state": current})

app = web.Application()
app.add_routes(routes)
web.run_app(app, port=args.port)
