"""This file just provides backward compatibility for the old, synchronous way of using this library"""
import asyncio

from typing import Awaitable, Optional, Dict

import pyrogram
from pyrogram.raw.base import InputPeer

from .js_core import INSTANCE as JSC
from .helpers import assert_version, event_handler
from .groupcall import GroupCall

class MissingClientException(Exception):
    pass

class PyTgCalls:
    def __init__(
        self,
        client: pyrogram.Client,
    ):
        self.client : pyrogram.Client = client
        self.calls : Dict[int, GroupCall] = {}

    def _run_bg(self, task:Awaitable, *args, **kwargs) -> asyncio.Task:
        return asyncio.get_event_loop().create_task(task(*args, **kwargs))

    def run(self, start_pyro=True):
        if not self.client:
            raise MissingClientException("Pyrogram client not configured")
        
        assert_version('node', '15')
        assert_version('pyrogram', '1.2', pyrogram.__version__)

        if start_pyro:
            self.client.run()

    def set_volume(self, chat_id:int, vol:int) -> None:
        self._run_bg(self.calls[chat_id].set_volume(vol))
    
    def pause_stream(self, chat_id:int) -> None:
        self._run_bg(self.calls[chat_id].pause_stream())

    def resume_stream(self, chat_id:int) -> None:
        self._run_bg(self.calls[chat_id].resume_stream())

    def change_stream(self, chat_id:int, file_path: str):
        self._run_bg(self.calls[chat_id].change_stream(file_path))

    def leave_group_call(self, chat_id:int, reason:str = 'committed sudoku'):
        t = self._run_bg(self.calls[chat_id].leave_group_call(reason))
        t.add_done_callback(lambda _: self._run_bg(JSC.clear(self.calls[chat_id].sid))) # EWWW!
        self.calls.pop(chat_id)

    def join_group_call(
            self,
            chat_id: int,
            file_path: str,
            bitrate: int = 48000,
            invite_hash: Optional[str] = None,
            join_as: Optional[InputPeer] = None,
    ) -> None:
        self.calls[chat_id] = GroupCall(self.client, chat_id)
        self._run_bg(self.calls[chat_id].join_group_call(file_path, bitrate, invite_hash, join_as))