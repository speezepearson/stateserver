import argparse
import asyncio
import collections
import dataclasses
import json
import pprint
from pathlib import Path
from typing import Mapping

from aiohttp import web

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--state-dir', type=Path, default=Path.cwd())
parser.add_argument('-p', '--port', type=int, default=8002)
args = parser.parse_args()

@dataclasses.dataclass
class Resource:
    path: Path

    def get(self):
        if self.path.is_file():
            return json.load(self.path.open())
        else:
            return None

    def put(self, j):
        json.dump(j, self.path.open('w'))

routes = web.RouteTableDef()
conditions: Mapping[str, asyncio.Condition] = collections.defaultdict(asyncio.Condition)

def get_state_path(name: str) -> Path:
    if not name.isalnum():
        raise ValueError(f'non alphanumeric: {name!r}')
    return (args.state_dir/name).with_suffix('.json')

@routes.route('GET', '/states/{name:[a-zA-Z0-9]{,32}}')
async def server_get_state(request: web.Request):
    name: str = request.match_info['name']
    assert name.isalnum()
    resource = Resource(get_state_path(name))
    print('GET /states/' + name)
    async with conditions[name]:
        return web.json_response({"current_state": resource.get()})

@routes.route('POST', '/poll/{name:[a-zA-Z0-9]{,32}}')
async def server_poll(request: web.Request):
    name: str = request.match_info['name']
    assert name.isalnum()
    resource = Resource(get_state_path(name))
    print('POST /poll/' + name)

    try:
        old_state = (await request.json())['current_state']
    except ValueError:
        return web.Response(body='syntactically invalid JSON request', status=400)
    except (TypeError, KeyError) as e:
        return web.Response(body=f'semantically invalid JSON request: {e}', status=400)
    condition = conditions[name]
    async with condition:
        await condition.wait_for(lambda: resource.get() != old_state)
        return web.json_response({"current_state": resource.get()})

@routes.route('POST', '/states/{name:[a-zA-Z0-9]{,32}}')
async def server_post_state(request: web.Request):
    name: str = request.match_info['name']
    assert name.isalnum()
    resource = Resource(get_state_path(name))
    print('POST /states/' + name)
    try:
        request_state = await request.json()
    except ValueError:
        return web.Response(body='syntactically invalid JSON request', status=400)
    if not (isinstance(request_state, dict) and set(request_state.keys()) == {'old', 'new'}):
        return web.Response(body='semantically invalid JSON request', status=400)
    request_old = request_state['old']
    request_new = request_state['new']

    async with conditions[name]:
        current = resource.get()
        if current == request_old:
            print("transitioning:")
            pprint.pprint(request_state)
            resource.put(request_new)
            conditions[name].notify_all()
            return web.json_response({"success": True, "current_state": request_new})
        else:
            print("not transitioning")
            pprint.pprint({"actual": current, "supposed": request_old, "desired": request_new})
            return web.json_response({"success": False, "current_state": current})

app = web.Application()
app.add_routes(routes)
web.run_app(app, port=args.port)
