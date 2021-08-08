import json
import functools

from typing import List

from pyrogram.raw.types import Updates, DataJSON
from pyrogram.raw.types.phone import GroupParticipants
from pyrogram.raw.functions.phone import (
    EditGroupCallParticipant, LeaveGroupCall, JoinGroupCall, GetGroupParticipants
)

from .base_session import BaseSession
from .has_cache import CacheHolder
from .call_holder import CallHolder

def check_session_id(fun):
    @functools.wraps(fun)
    async def wrapper(ctx:BaseSession, session_id:str, *args, **kwargs):
        if session_id == ctx.sid:
            return await fun(*args, **kwargs)
        return None
    return wrapper

class CallbacksHolder(CacheHolder, CallHolder):
    @check_session_id
    async def _change_volume_voice_call(self, chat_id:int, volume:int) -> dict:
        chat_call = await self.fetch_call(chat_id)
        await self.client.send(
            EditGroupCallParticipant(
                call=chat_call,
                participant=self.peer_cache.get(chat_id),
                muted=False,
                volume=volume * 100,
            ),
        )
        return {'result':'OK'}

    @check_session_id
    async def _event_finish(self, chat_id:int) -> dict:
        self.remove_active_call(chat_id)

        # TODO event handler trait
        # for event in self.pytgcalls._on_event_update['STREAM_END_HANDLER']:
        #     self.pytgcalls.run_async(
        #         event['callable'],
        #         (chat_id,),
        #     )
        return {'result':'OK'}

    @check_session_id
    async def _get_participants(self, chat_id:int) -> List[dict]:
        participants: GroupParticipants = await self.client.send(
            GetGroupParticipants(
                call=await self.fetch_call(chat_id),
                ids=[],
                sources=[],
                offset='',
                limit=5000,
            ),
        )
        return [
            {'source': x.source, 'user_id': x.peer.user_id}
            for x in participants.participants
        ]

    @check_session_id
    async def _update_call_data(self, chat_id:int, result:str) -> dict:
        if result == 'PAUSED_AUDIO_STREAM':
            self.set_status(chat_id, 'paused')
        elif result == 'RESUMED_AUDIO_STREAM':
            self.set_status(chat_id, 'playing')
        elif result == 'JOINED_VOICE_CHAT' or \
                result == 'CHANGED_AUDIO_STREAM':
            self.add_active_call(chat_id)
            self.add_call(chat_id)
            self.set_status(chat_id, 'playing')
        elif result == 'LEFT_VOICE_CHAT' or \
                result == 'KICKED_FROM_GROUP':
            self.remove_active_call(chat_id)
            self.remove_call(chat_id)
        # TODO event handling trait
        # for event in self.pytgcalls._on_event_update[
        #     'EVENT_UPDATE_HANDLER'
        # ]:
        #     self.pytgcalls.run_async(
        #         event['callable'],
        #         (params,),
        #     )
        return {'result':'OK'}

    # @check_session_id
    # async def _api_backend(self, chat_id:int) -> dict:
    #     res = 'FAIL'
    #     try:
    #         await self.pytgcalls._sio.emit('request', json.dumps(params))
    #         result_json = {
    #             'result': 'ACCESS_GRANTED',
    #         }
    #     except Exception:
    #         pass
    #     return {'result' : res}

    # @check_session_id
    # async def _custom_api_update(self, **kwargs):
    #     # TODO event handlers!
    #     # handler = self.pytgcalls._on_event_update['CUSTOM_API_HANDLER'][0]
    #     # return await handler['callable'](**kwargs)
    #     return {}

    @check_session_id
    async def _leave_voice_call(self, chat_id:int) -> dict:
        chat_call = await self.fetch_call(chat_id)
        if chat_call:
            await self.client.send(
                LeaveGroupCall(
                    call=chat_call,
                    source=0,
                ),
            )
        return {'result':'OK' if chat_call else 'FAIL'}

    @check_session_id
    async def _join_voice_call(self,
            chat_id:int,
            urfrag:str,
            pwd:str,
            hash:str,
            setup:str,
            fingerprint:str,
            source:str,
            invite_hash:str = "",
    ) -> dict:
        request_call = {
            'ufrag': urfrag,
            'pwd': pwd,
            'fingerprints': [{
                'hash': hash,
                'setup': setup,
                'fingerprint': fingerprint,
            }],
            'ssrc': source,
        }
        chat_call = await self.fetch_call(chat_id)
        result: Updates = await self.client.send(
            JoinGroupCall(
                call=chat_call,
                params=DataJSON(data=json.dumps(request_call)),
                muted=False,
                join_as=self.pytgcalls.peer_cache.get(chat_id),
                invite_hash=invite_hash,
            ),
        )

        # TODO jank! do this in a proper raw_updates_handler
        transport = json.loads(result.updates[0].call.params.data)['transport']

        return {
            'transport': {
                'ufrag': transport['ufrag'],
                'pwd': transport['pwd'],
                'fingerprints': transport['fingerprints'],
                'candidates': transport['candidates'],
            },
        }
