from pyrogram import Client
from pyrogram.raw.base import InputPeer
from pyrogram.types import User

from .base_session import BaseSession
from .call_holder import CallHolder
from .client_session import ClientSession
from .controllable import Controllable
from .has_cache import CacheHolder
from .has_callbacks import CallbacksHolder

class Scaffolding(
    Controllable,
    CallbacksHolder
):
    pass