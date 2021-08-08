import logging
import asyncio

from time import time
from typing import Callable
from typing import Dict
from typing import List

import pyrogram

from .js_core import INSTANCE as jscore
from .http_bridge import INSTANCE as bridge
from .helpers import HandlersHolder, TimedCache, VersionNumber, get_version, generate_session_id
from .events.handlers import event_handler

from .traits import Scaffolding

class MissingClientException(Exception):
    pass

class DependancyException(Exception):
    pass

class PyTgCalls(Scaffolding):
    def __init__(
        self,
        client: pyrogram.Client,
        port: int = 24859,
        log_mode: int = 0,
        flood_wait_cache: int = 120,
    ):
        super().__init__()
        # TODO load these settings from config maybe?
        self.host : str = '127.0.0.1'
        self.port : int = port
        self._on_event_update: HandlersHolder = HandlersHolder()
        self._flood_wait_cache = flood_wait_cache
        self.log_mode : int = log_mode
        asyncio.get_event_loop().create_task(self.set_client(client)) # with I had async constructors...

    async def run(self, before_start_callable: Callable = None):
        if not self.client:
            raise MissingClientException("Pyrogram client not configured")
        
        node_v = get_version('node')
        if not node_v:
            raise DependancyException("Could not find node.js, please install v15+")
        if node_v < 15:
            raise DependancyException(f"node.js v15+ required, found version {node_v}")

        pyrogram_version = VersionNumber(pyrogram.__version__)
        if pyrogram_version < '1.2':
            raise DependancyException(f"pyrogram v1.2.0+ required, found version {pyrogram_version}")

        self.client.on_raw_update()(event_handler(self))

        if before_start_callable is not None:
            try: # WTF is this
                result = before_start_callable(self.me.id)
                if isinstance(result, bool) and not result:
                    return
            except Exception:
                logging.exception("Exception in before_start callback")
                    

        jscore.start(port=self.port, log_mode=self.log_mode)
        await bridge.start(self.host, self.port)

        return self

    def _add_handler(self, type_event: str, func):
        self._on_event_update[type_event].append(func)
