import functools
import logging
import json

from typing import Callable, Dict, List
from aiohttp import web, ClientSession

async def base_route(ctx : 'HttpBridge', request : web.Request) -> web.Response:
    params = await request.json()
    event = request.path.split('/')[-1]
    res = None
    if event in ctx.handlers:
        for fn in list(ctx.handlers[event]): # make a copy
            try:
                buf = await fn(**params)
                res = res or buf
            except Exception:
                logging.exception(
                    "Exception in callback '%s' for event '%s' with payload '%s'",
                    fn.__name__, event, str(params)
                )
    if not res:
        res = {'result':'0 handlers triggered'}
    return web.json_response(json.dumps(res))


class HttpBridge:
    def __init__(self):
        self.app : web.Application = web.Application()
        self.runner : web.AppRunner = None
        self.handlers : Dict[str, List[Callable]] = {}
        self.app.router.add_post("*", functools.partial(base_route, self))

        # self.app.add_routes([
        #     web.post('/request_join_call', self.pytgcalls._join_voice_call),
        #     web.post('/request_leave_call', self.pytgcalls._leave_voice_call),
        #     web.post('/get_participants', self.pytgcalls._get_participants),
        #     web.post('/ended_stream', self.pytgcalls._event_finish),
        #     web.post('/update_request', self.pytgcalls._update_call_data),
        #     web.post('/api_internal', self.pytgcalls._api_backend),
        #     web.post('/request_change_volume', self.pytgcalls._change_volume_voice_call),
        #     web.post('/async_request', self.pytgcalls._async_result),
        # ])
        # if len(self.pytgcalls._on_event_update['CUSTOM_API_HANDLER']) > 0:
        #     self.pytgcalls._app_core.router.add_post(
        #         '/api', self.pytgcalls._custom_api_update,
        #     )
        # noinspection PyTypeChecker

    @property
    def running(self):
        return self.runner is not None

    def on(self, event:str) -> Callable:
        def decorator(func):
            if event not in self.handlers:
                self.handlers[event] = []
            self.handlers[event].append(func)
            return func
        return decorator

    async def post(self, url:str, data:dict) -> bool:
        with ClientSession() as sess:
            with sess.post(url, data=json.dumps(data).encode('utf-8')) as res:
                pass


    async def start(self, host:str = 'localhost', port:int = 6969) -> bool:
        if self.running:
            return False
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        return True

    async def stop(self) -> bool:
        if not self.running:
            return False
        await self.runner.cleanup()
        self.runner = None
        return True

INSTANCE = HttpBridge()