import os

from signal import SIGINT
from subprocess import Popen, PIPE, TimeoutExpired

class JSCore:
    def __init__(self):
        self.proc : Popen = None
        self._stdout : bytes = b''
        self._stderr : bytes = b''

    @property
    def running(self) -> bool:
        """Check if NodeJS core is already running"""
        if self.proc is not None:
            if self.proc.poll() is not None:
                return True
        return False

    def start(self, port:int = 6969, log_mode:str = "") -> bool:
        """Will start the NodeJS core if not running.
        Returns True if a node process was started"""
        if self.running:
            return False
        js_file = os.getcwd() + os.path.sep + "dist" + os.path.sep + "index.js"
        self.proc = Popen(["node", js_file, f"port={port}", f"log_mode={log_mode}"], stdout=PIPE, stderr=PIPE) # bot sure about the port=123 and log_mode=...
        return True

    def stop(self, timeout:float=3.0):
        """Will attempt to terminate gracefully the NodeJS core and wait until timeout (default 3s).
        If the application won't exit by then, a SIGKILL will be sent."""
        try:
            self.proc.send_signal(SIGINT)
            self._stdout, self._stderr = self.proc.communicate(timeout=timeout)
        except TimeoutExpired:
            self.proc.kill()
            self._stdout, self._stderr = self.proc.communicate()

INSTANCE = JSCore()