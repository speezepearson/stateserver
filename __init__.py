import argparse
import asyncio
import collections
import json

from functools import partial
from pathlib import Path
from typing import Iterable, Mapping, NamedTuple, NewType

from aiohttp import web

ResourceName = NewType('ResourceName', str)

def allow_all_origins(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

class Resource(NamedTuple): # would like to use dataclasses, but installing 3.7 is nontrivial
    path: Path

    def get(self):
        if self.path.is_file():
            return json.load(self.path.open())
        else:
            return None

    def put(self, j):
        json.dump(j, self.path.open('w'))

def make_routes(state_dir: Path) -> Iterable[web.RouteDef]:
    conditions: Mapping[ResourceName, asyncio.Condition] = collections.defaultdict(asyncio.Condition)
    for method, path, func in [('GET', '/{name:[a-zA-Z0-9]{,32}}', get_state_response),
                               ('POST', '/{name:[a-zA-Z0-9]{,32}}/poll', poll_response),
                               ('POST', '/{name:[a-zA-Z0-9]{,32}}', post_state_response),
                               ]:
        yield web.route(method, path, partial(func, state_dir=state_dir, conditions=conditions))


def get_state_path(state_dir: Path, name: ResourceName) -> Path:
    if not name.isalnum():
        raise ValueError(f'non alphanumeric: {name!r}')
    return (state_dir/name).with_suffix('.json')

async def get_state_response(request: web.Request, state_dir: Path, conditions: Mapping[ResourceName, asyncio.Condition]):
    name: ResourceName = request.match_info['name']
    resource = Resource(get_state_path(state_dir, name))
    async with conditions[name]:
        return allow_all_origins(web.json_response({"current_state": resource.get()}))

async def poll_response(request: web.Request, state_dir: Path, conditions: Mapping[ResourceName, asyncio.Condition]):
    name: ResourceName = request.match_info['name']
    resource = Resource(get_state_path(state_dir, name))

    try:
        old_state = (await request.json())['current_state']
    except ValueError:
        return allow_all_origins(web.Response(body='syntactically invalid JSON request', status=400))
    except (TypeError, KeyError) as e:
        return allow_all_origins(web.Response(body=f'semantically invalid JSON request: {e}', status=400))
    condition = conditions[name]
    async with condition:
        await condition.wait_for(lambda: resource.get() != old_state)
        return allow_all_origins(web.json_response({"current_state": resource.get()}))

async def post_state_response(request: web.Request, state_dir: Path, conditions: Mapping[ResourceName, asyncio.Condition]):
    name: ResourceName = request.match_info['name']
    resource = Resource(get_state_path(state_dir, name))
    try:
        request_state = await request.json()
    except ValueError:
        return allow_all_origins(web.Response(body='syntactically invalid JSON request', status=400))
    if not (isinstance(request_state, dict) and set(request_state.keys()) == {'old', 'new'}):
        return allow_all_origins(web.Response(body='semantically invalid JSON request', status=400))
    request_old = request_state['old']
    request_new = request_state['new']

    async with conditions[name]:
        current = resource.get()
        if current == request_old:
            resource.put(request_new)
            conditions[name].notify_all()
            return allow_all_origins(web.json_response({"success": True, "current_state": request_new}))
        else:
            return allow_all_origins(web.json_response({"success": False, "current_state": current}))
