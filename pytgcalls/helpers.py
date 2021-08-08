import re
import string
import logging
import secrets

from time import time
from enum import Enum
from typing import Callable, Union, List, Any, Optional
from functools import total_ordering
from subprocess import Popen, PIPE

from dataclasses import dataclass

from pyrogram import ContinuePropagation
from pyrogram.raw.types import ChannelForbidden
from pyrogram.raw.types import GroupCall
from pyrogram.raw.types import GroupCallDiscarded
from pyrogram.raw.types import InputGroupCall
from pyrogram.raw.types import MessageActionInviteToGroupCall
from pyrogram.raw.types import UpdateChannel
from pyrogram.raw.types import UpdateGroupCall
from pyrogram.raw.types import UpdateNewChannelMessage

from .pytgcalls import PyTgCalls

class BColors(Enum):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

@dataclass
class HandlersHolder:
    update : List[Callable] = []
    stream_end : List[Callable] = []
    custom_api : List[Callable] = []
    group_call : List[Callable] = []
    kicked : List[Callable] = []
    closed : List[Callable] = []

    def __getitem__(self, name:str) -> Any:
        return getattr(self, name)

def _compare_versions(a : List[int], b : List[int]):
    min_depth = min(len(a), len(b))
    max_depth = max(len(a), len(b))
    # check against each other as long as they have same length
    for i in range(min_depth):
        if a[i] > b[i]:
            return 1
        elif a[i] < b[i]:
            return -1
    # if one is longer, it's bigger as long as it's >0
    for i in range(min_depth, max_depth):
        if len(a) > min_depth and a[i] > 0:
            return 1
        elif len(b) > min_depth and b[i] > 0:
            return -1
    return 0

@total_ordering
class VersionNumber:
    """Wrapper object around List[int] for easy version comparisons

    will accept strings, single integers and lists of integers for comparisons
        v = VersionNumber("10.0.1")
        v > 10 # True
        v > '10.0.0' # True
        v < [10, 0] # False
    """
    def __init__(self, version : Union[str, int, List[int]]):
        if isinstance(version, str):
            self.v = [ int(v) for v in version.split('.') ]
        elif isinstance(version, int):
            self.v = [version]
        elif isinstance(version, list):
            self.v = version
        else:
            raise ValueError("Invalid value for version, must be str, int or list[int]")

    def __getitem__(self, index:int) -> int:
        return self.v[index]

    def __len__(self) -> int:
        return len(self.v)

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return '.'.join([ str(v) for v in self.v ])

    def __eq__(self, other : Any) -> bool:
        if not isinstance(other, VersionNumber):
            other = VersionNumber(other)
        return _compare_versions(self.v, other.v) == 0

    def __gt__(self, other : Any) -> bool:
        if not isinstance(other, VersionNumber):
            other = VersionNumber(other)
        return _compare_versions(self.v, other.v) > 0

    def __lt__(self, other : Any) -> bool:
        if not isinstance(other, VersionNumber):
            other = VersionNumber(other)
        return _compare_versions(self.v, other.v) < 0

FIND_V_NUMBER = re.compile(r"[0-9\.]+")
def get_version(pkg : str) -> VersionNumber:
    proc = Popen([pkg, '--version'], stderr=PIPE, stdout=PIPE)
    stdout, _stderr = proc.communicate()
    v = stdout.decode('utf-8').strip()
    if not v:
        return None
    match = FIND_V_NUMBER.search(v)
    if not match:
        return None
    return VersionNumber(match.group(0))

@dataclass
class CacheEntry:
    time : int
    data : Any

class TimedCache:
    def __init__(self):
        self.store = {}

    def get(self, id:int) -> Optional[dict]:
        if id in self.store:
            return self.store[id]
        return None

    def put(self, id:int, data:Any) -> None:
        self.store[id] = CacheEntry(time=time(), data=data)

    def pop(self, id:int) -> Optional[Any]:
        return self.store.pop(id, None)

def generate_session_id(length) -> str:
    letters = string.ascii_lowercase # Use secrets rather than random just in case
    return ''.join(secrets.choice(letters) for _ in range(length))

class PyLogs:
    ultra_verbose = 2
    verbose = 1

class StreamType(Enum):
    LIVE = 3
    LOCAL = 10
    """
    *** Beta Pulse Stream ***
    Send bytes like a pulsation, and this reduce the slice,
    because the slice is too heavy

    Support: LiveStream, LocalStream
    """
    PULSE = 4


def event_handler(pytgcalls : PyTgCalls):
    async def handler(client, update, users, chats):
        if isinstance(update, UpdateChannel) and update.channel_id in chats and \
                isinstance(chats[update.channel_id], ChannelForbidden): # Check if any channel became forbidden
            chat_id = int(f'-100{update.channel_id}')
            for event in pytgcalls._on_event_update.kick:
                await event(chat_id)
            try:
                pytgcalls.leave_group_call(chat_id, 'kicked_from_group')
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