from typing import List, Dict

from .client_session import ClientSession

class CallHolder(ClientSession):
    """WTF is this class, why the difference, why a list and a dict!!!!"""
    def __init__(self):
        self.calls : List[int] = []
        self.active_calls : Dict[int, str] = {}

    def add_call(self, chat_id:int) -> None:
        self.calls.append(chat_id)
    
    def add_active_call(self, chat_id:int) -> None:
        self.active_calls[chat_id] = 'playing' # WTF WHYYY

    def remove_call(self, chat_id:int) -> None:
        if chat_id in self._calls:
            self.calls.remove(chat_id)

    def remove_active_call(self, chat_id:int) -> None:
        self.active_calls.pop(chat_id, None)

    def set_status(self, chat_id:int, status:str) -> None:
        self.active_calls[chat_id] = status
