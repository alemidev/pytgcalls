import logging
import asyncio

from time import time
from typing import Callable
from typing import Dict
from typing import List

import pyrogram

from .js_core import INSTANCE as jscore
from .helpers import assert_version, event_handler

from .traits import Scaffolding

class MissingClientException(Exception):
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
        self._flood_wait_cache = flood_wait_cache
        self.log_mode : int = log_mode
        asyncio.get_event_loop().create_task(self.set_client(client)) # wish I had async constructors...

    async def run(self, before_start_callable: Callable = None):
        if not self.client:
            raise MissingClientException("Pyrogram client not configured")
        
        assert_version('node', '15')
        assert_version('pyrogram', '1.2', pyrogram.__version__)

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
