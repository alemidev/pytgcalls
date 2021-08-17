import re
import logging

from pkg_resources import parse_version
from typing import Any, Optional
from subprocess import Popen, PIPE

from pyrogram import ContinuePropagation
from pyrogram.raw.types import ChannelForbidden
from pyrogram.raw.types import GroupCall
from pyrogram.raw.types import GroupCallDiscarded
from pyrogram.raw.types import InputGroupCall
from pyrogram.raw.types import MessageActionInviteToGroupCall
from pyrogram.raw.types import UpdateChannel
from pyrogram.raw.types import UpdateGroupCall
from pyrogram.raw.types import UpdateNewChannelMessage

from .call import Call

class DependancyException(Exception):
    pass

FIND_V_NUMBER = re.compile(r"[0-9\.]+")
def _get_version(pkg : str) -> str:
    proc = Popen([pkg, '--version'], stderr=PIPE, stdout=PIPE)
    stdout, _stderr = proc.communicate()
    v = stdout.decode('utf-8').strip()
    if not v:
        raise DependancyException(f"Dependancy '{pkg}' could not be found")
    match = FIND_V_NUMBER.search(v)
    if not match:
        raise DependancyException(f"Dependancy '{pkg}' didn't provide valid version number: '{v}'")
    return match.group(0)

def assert_version(pkg: str, min_v:str, curr_v:Optional[str] = None) -> None:
    if not curr_v:
        curr_v = _get_version(pkg)
    if parse_version(curr_v) < parse_version(min_v):
        raise DependancyException(f"Dependancy '{pkg}' requires version {min_v}+, found {curr_v}")

def event_handler(ctx : Call):
    async def handler(client, update, users, chats):
        if isinstance(update, UpdateChannel) and update.channel_id in chats and \
                isinstance(chats[update.channel_id], ChannelForbidden): # Check if any channel became forbidden
            chat_id = int(f'-100{update.channel_id}')
            for event in pytgcalls._on_event_update.kick:
                await event(chat_id)
            try:
                ctx.leave_group_call('kicked_from_group')
            except Exception:
                logging.exception("Exception while leaving group call when kicked")
            pytgcalls.peer_cache.pop(chat_id)
        if isinstance(update, UpdateGroupCall):
            if isinstance(update.call, GroupCall):
                pytgcalls.chat_cache.put(
                    int(f'-100{update.chat_id}'),
                    InputGroupCall(
                        access_hash=update.call.access_hash,
                        id=update.call.id,
                    )
                )
            if isinstance(update.call, GroupCallDiscarded):
                chat_id = int(f'-100{update.chat_id}')
                for event in pytgcalls._on_event_update.closed:
                    await event(chat_id)
                try:
                    pytgcalls.leave_group_call(chat_id, 'closed_voice_chat')
                except Exception:
                    logging.exception("Exception while leaving group call when closed")
                pytgcalls.peer_cache.pop(chat_id)
                pytgcalls.chat_cache.put(chat_id, None)
        if isinstance(update, UpdateNewChannelMessage):
            try: # wtf is this
                if isinstance(update.message.action, MessageActionInviteToGroupCall):
                    for event in pytgcalls._on_event_update.group_call:
                        await event(client, update.message)
            except Exception:
                logging.exception("Exception trying to run GROUP_CALL callbacks")
        raise ContinuePropagation() # so that it won't ever shadow other handlers

    return handler