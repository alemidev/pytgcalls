import os
import json
import asyncio
from uuid import uuid4

from typing import Awaitable, Callable, Optional

from pyrogram import Client
from pyrogram.raw.functions.phone import JoinGroupCall, LeaveGroupCall, EditGroupCallParticipant
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.base import InputPeer, DataJSON

from .js_core import INSTANCE as JSC

from .helpers import event_handler

class GroupCall:
    def __init__(self, client:Client, chat_id:int) -> bool:
        self.client = client
        self.chat_id : int = chat_id
        self.initialized : asyncio.Event = asyncio.Event()
        self.request : dict = None
        self.sid : str = str(uuid4())
        # Register the event handler to process groupcall transport events
        self.client.on_raw_update()(event_handler(self))
        # Fetch everything in background
        asyncio.get_event_loop().create_task(self._build_cache())

    async def _build_cache(self):
        self.me = await self.client.get_me()
        self.peer = await self.client.resolve_peer(self.me.id)
        self.chat = await self.client.get_chat(self.chat_id)
        chat_peer = await self.client.resolve_peer(self.chat_id)
        self.full_chat = await self.client.send(GetFullChannel(channel=chat_peer))
        self.call = self.full_chat.full_chat.call # TODO this might not exist right away?
        self.initialized.set()

    @property
    def state(self) -> Optional[str]:
        return JSC.state(self.sid)

    def on(self, event:str) -> Callable:
        return JSC.on(self.sid, event)

    async def _stream_action(self, action:str, extra:Optional[dict] = None) -> None:
        await JSC.send( # merge the 2 dictionaries, in py 3.9+ extra | {'action':...}
            **( extra or {} ),
            **{
                # 'session_id': self.sid,
                'action': action,
                'chat_id': self.chat_id,
            }
        )

    async def set_volume(self, vol:int) -> None:
        # await self._stream_action('volume', {'volume':vol})
        await self.client.send(
            EditGroupCallParticipant(
                call=self.call,
                participant=self.peer,
                muted=False,
                volume=max(0, min(vol, 100)),
            ),
        )
    
    async def pause_stream(self) -> None:
        await self._stream_action('pause')

    async def resume_stream(self) -> None:
        await self._stream_action('resume')

    async def change_stream(self, file_path: str):
        await self._stream_action('change_stream', {'file_path':file_path})

    async def leave_group_call(self, reason: str = 'committed sudoku'):
        await self._stream_action('leave_call', {'type':reason})
        # await JSC.clear(self.sid)
        self.sid = ''
        await self.client.send(
            LeaveGroupCall(
                call=self.call,
                source=0,
            ),
        )

    async def join_group_call(
            self,
            file_path: str,
            bitrate: int = 48000,
            invite_hash: Optional[str] = None,
            join_as: Optional[InputPeer] = None,
    ) -> None:
        await self.initialized.wait()
        if not os.path.isfile(file_path):
            raise ValueError("Invalid file provided")
        if join_as is None:
            join_as = self.peer
        # PC.set(self.chat_id, join_as)
        bitrate = min(bitrate, 48000)
        await JSC.init(self.sid)
        res = await JSC.send(
            {
                'action': 'join_call',
                'chat_id': self.chat_id,
                'file_path': file_path,
                'invite_hash': invite_hash,
                'bitrate': bitrate,
                # 'session_id': self.sid,
                # 'buffer_long': stream_type.value,
            }
        )
        self.request = {
            'ufrag': res['urfrag'],
            'pwd': res['pwd'],
            'fingerprints': [{
                'hash': res['hash'],
                'setup': res['setup'],
                'fingerprint': res['fingerprint'],
            }],
            'ssrc': res['source'],
        }
        await self.client.handle_updates(
            await self.client.send(
                JoinGroupCall(
                    call=self.call,
                    params=DataJSON(data=json.dumps(self.request)),
                    muted=False,
                    join_as=join_as,
                    invite_hash=invite_hash,
                ),
            )
        )