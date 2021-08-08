from ..helpers import generate_session_id

class BaseSession:
    sid : str
    
    def __init__(self):
        self.sid = generate_session_id(20)