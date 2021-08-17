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

def check_session_id(fun):
    @functools.wraps(fun)
    async def wrapper(ctx:BaseSession, *args, **kwargs):
        if 'session_id' not in kwargs:
            raise Exception("Received event without 'session_id'")
        if kwargs['session_id'] == ctx.sid:
            return await fun(*args, **kwargs)
        return None
    return wrapper

class CallbacksHolder(CacheHolder):
    def __init__(self):
        self.callbacks = (
            ('request_change_volume', self._change_volume_voice_call),
            ('ended_stream', self._event_finish),
            ('get_participants', self._get_partecipants),
            ('update_request', self._update_call_data),
            # ('api_internal', self._api_backend),
            # ('api', self._custom_api_update),
            ('request_leave_call', self._leave_voice_call),
            ('request_join_call', self._join_voice_call),
        )
        for event, cb in self.callbacks:
            bridge.on(event)(cb)

    def __del__(self):
        for event, cb in self.callbacks:
            bridge.rm(event)(cb)
        super().__del__()

    def on_stream_end(self):
        def decorator(fun):
            bridge.on('ended_stream')(fun)
            return fun
        return decorator

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
    async def _get_partecipants(self, chat_id:int) -> List[dict]:
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