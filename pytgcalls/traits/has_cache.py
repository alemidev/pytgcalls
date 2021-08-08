import logging
from time import time

from pyrogram.raw.types import ChatFull
from pyrogram.raw.functions.channels import GetFullChannel

from ..helpers import TimedCache
from .client_session import ClientSession

class CacheHolder(ClientSession):
    peer_cache: TimedCache = TimedCache()
    chat_cache: TimedCache = TimedCache()

    async def fetch_call(self, chat_id: int) -> ChatFull:
        cached = self.chat_cache.get(chat_id)
        if time() - cached.time < self._flood_wait_cache: # TODO receive this somehow
            logging.debug("[%s] FullChat cache hit for %d", self.sid, chat_id)
            return cached.data
        logging.debug("[%s] FullChat cache miss for %d", self.sid, chat_id)
        chat = await self.client.resolve_peer(chat_id)
        full_chat = await self.client.send(GetFullChannel(channel=chat))
        full_chat = full_chat.full_chat.call
        self.chat_cache.put(chat_id, full_chat)
        return full_chat
