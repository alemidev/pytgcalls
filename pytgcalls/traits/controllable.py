import os

from typing import Optional

from pyrogram.raw.base import InputPeer

from .has_cache import CacheHolder
from ..helpers import StreamType

from ..http_bridge import INSTANCE as bridge


class Controllable(CacheHolder):
    async def join_group_call(
            self,
            chat_id: int,
            file_path: str,
            bitrate: int = 48000,
            invite_hash: Optional[str] = None,
            join_as: Optional[InputPeer] = None,
            stream_type: StreamType = StreamType["LOCAL"],
    ):
        if join_as is None:
            join_as = self.peer
        if os.path.getsize(file_path) == 0: # not sure this is necessary, nor the best way to do it
            raise Exception('Error internal: INVALID_FILE_STREAM')
        self.peer_cache.set(chat_id, join_as)
        bitrate = 48000 if bitrate > 48000 else bitrate
        await bridge.post(
            '/api_internal',
            {
                'session_id': self.sid,
                'action': 'join_call',
                'chat_id': chat_id,
                'file_path': file_path,
                'invite_hash': invite_hash,
                'bitrate': bitrate,
                'buffer_long': stream_type.value,
            }
        )

    async def leave_group_call(self, chat_id: int, type_leave: str = 'requested'):
        await bridge.post(
            '/api_internal',
            {
                'session_id': self.sid,
                'action': 'leave_call',
                'chat_id': chat_id,
                'type': type_leave,
            }
        )

    async def change_volume_call(self, chat_id: int, volume: int):
        volume = min(max(volume, 0), 200)
        await bridge.post(
            '/request_change_volume',
            {
                "session_id": self.sid,
                "chat_id": chat_id,
                "volume": volume,
            }
        )

    async def change_stream(self, chat_id: int, file_path: str):
        await bridge.post(
            '/api_internal',
            {
                'session_id': self.sid,
                'action': 'change_stream',
                'chat_id': chat_id,
                'file_path': file_path,
            }
        )

    async def resume_stream(self, chat_id: int):
        await bridge.post(
            '/api_internal',
            {
                'session_id': self.sid,
                'action': 'resume',
                'chat_id': chat_id,
            }
        )

    async def pause_stream(self, chat_id: int):
        await bridge.post(
            '/api_internal',
            {
                'session_id': self.sid,
                'action': 'pause',
                'chat_id': chat_id,
            }
        )