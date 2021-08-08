from pyrogram import Client
from pyrogram.types import User
from pyrogram.raw.base import InputPeer

from .base_session import BaseSession

class ClientSession(BaseSession):
    client : Client
    me : User
    peer : InputPeer

    async def set_client(self, client:Client) -> None:
        self.client = client
        self.me = await self.client.get_me()
        self.peer = await client.resolve_peer(self.me.id)