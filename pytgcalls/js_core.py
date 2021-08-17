import os
import json
import sys
import asyncio
import logging

from uuid import uuid4
from asyncio.subprocess import Process

from signal import SIGINT
from subprocess import PIPE

from typing import Dict, Tuple, Any, List, Union, Optional, Awaitable, Generator, Callable

from .helpers import assert_version

logger = logging.getLogger(__name__)

class InvalidState(Exception):
    pass

class JSCore:
    def __init__(self):
        assert_version('node', '15')
        self.proc : Process = None
        self.packet_count : int = 0
        self.waiting : Dict[int, asyncio.Future] = {}
        self.sessions : Dict[str, str] = {}
        self.callbacks : Dict[str, Dict[str, List[Awaitable]]] = {}

    @property
    def running(self) -> bool:
        """Check if NodeJS core is already running"""
        if self.proc and self.proc.returncode is None:
            return True
        return False

    async def __aiter__(self) -> Generator[Tuple[dict, str, int, str], Any, None]: # This was a cool 2-liner but like this it's more reliable
        while self.running:
            buf = await self.proc.stdout.readline()
            try:
                packet = json.loads(buf)
            except json.JSONDecodeError:
                logger.exception("Could not deserialize packet '%s'", buf)
                continue
            if not all(k in packet for k in ("sid", "pid", "_")):
                logger.error("Ignoring packet with missing slots : %s", str(packet))
                continue
            yield packet, packet["sid"], packet["pid"], packet["_"].lower()

    async def _send(self, packet:bytes) -> None:
        self.proc.stdin.write(packet + b'\n')
        await self.proc.stdin.drain()

    async def _event_worker(self) -> None:
        logger.debug("Starting packet worker")
        async for packet, sid, pid, type in self:
            try:
                logger.debug("Processing event '%d' [%s] | %s", pid, type, str(packet))
                if type == "ack":
                    self.waiting[pid].set_result(packet)
                elif type == "status":
                    self.sessions[sid] = packet['status']
                elif type == "event" and sid in self.callbacks:
                    if packet["event"] in self.callbacks[sid]:
                        for cb in self.callbacks[sid][packet["event"]]:
                            asyncio.get_event_loop().create_task(cb(packet)) # can't block the worker
                else:
                    logger.warning("Unexpected packet type '%s'", type)
            except Exception: # this background worker must not die, catch very broadly
                logger.exception("Exception processing packet '%s'", str(packet))
        logger.debug("Stopping packet worker")

    def on(self, sid:str, event:str) -> Callable:
        def decorator(fun:Awaitable) -> Awaitable:
            if sid not in self.callbacks:
                self.callbacks[sid] = {}
            if event not in self.callbacks[sid]:
                self.callbacks[sid][event] = []
            self.callbacks[sid][event].append(fun)
            return fun
        return decorator

    def state(self, sid:str) -> Optional[str]:
        if sid not in self.sessions:
            return None
        return self.sessions[sid]

    async def send(self, sid:str, packet:dict) -> dict:
        if not self.running:
            raise InvalidState("Session not initialized")
        pid = self.packet_count
        self.packet_count += 1
        packet["pid"] = pid
        packet["sid"] = sid
        future = asyncio.get_event_loop().create_future()
        self.waiting[pid] = future
        buf = json.dumps(packet).encode('utf-8')
        await self._send(buf)
        return await future

    async def init(self, sid:str) -> str:
        if not self.running:
            await self._start()
        self.sessions[sid] = 'new'
        self.callbacks[sid] = {}
        # setup session on js side?
        return sid

    async def clear(self, sid:str) -> None:
        self.sessions.pop(sid)
        self.callbacks.pop(sid)
        # clear js side too maybe?
        if len(self.sessions) < 1:
            # asyncio.get_event_loop().create_task(self._stop())
            await self._stop()

    async def _start(self) -> None:
        """Will start the NodeJS core if not running.
        Returns True if a node process was started"""
        if self.running:
            raise InvalidState("NodeJS is already running")
        js_file = os.getcwd() + os.path.sep + "dist" + os.path.sep + "index.js"
        self.proc = await asyncio.create_subprocess_exec(
            "node", js_file,
            stdin=PIPE,
            stdout=PIPE,
            stderr=sys.stderr,
        )
        asyncio.get_event_loop().create_task(self._event_worker())
        logger.info("NodeJS started")

    async def _stop(self, timeout:float=3.0) -> None:
        """Will attempt to terminate gracefully the NodeJS core and wait until timeout (default 3s).
        If the application won't exit by then, a SIGKILL will be sent."""
        if not self.running:
            raise InvalidState("NodeJS is not running")
        try:
            self.proc.send_signal(SIGINT)
            await asyncio.wait_for(self.proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("NodeJS did not terminate cleanly, killing process...")
            self.proc.kill()
            await self.proc.communicate()
        logger.info("NodeJS stopped")

INSTANCE = JSCore()