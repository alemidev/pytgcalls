from enum import Enum
from typing import Callable, Dict, List

from .base_session import BaseSession

class EventType(Enum):
    custom_api = -1
    raw = 0
    stream_end = 1
    invite = 2
    kicked = 3
    closed = 4

class EventBus(BaseSession):
    callbacks : Dict[EventType, List[Callable]]

    def __init__(self):
        self.callbacks = {}

    def _handle(self, event:EventType):
        def decorator(func):
            if event not in self.callbacks:
                self.callbacks[event] = []
            self.callbacks[event].append(func)
            return func
        return decorator

    def on_closed_voice_chat(self) -> Callable:
        return self._handle(EventType['closed'])

    def on_group_call_invite(self) -> Callable:
        return self._handle(EventType['invite'])

    def on_stream_end(self) -> Callable:
        return self._handle(EventType['stream_end'])

    def on_kicked(self) -> Callable:
        return self._handle(EventType['kicked'])

    def on_raw_event(self) -> Callable:
        return self._handle(EventType['raw'])

    def on_update_custom_api(self) -> Callable:
        return self._handle(EventType['custom_api'])

