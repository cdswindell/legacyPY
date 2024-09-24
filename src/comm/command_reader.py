from __future__ import annotations

import threading
from collections import deque
from threading import Thread

from ..protocol.command_req import TMCC_FIRST_BYTE_TO_INTERPRETER
from ..protocol.constants import DEFAULT_BAUDRATE, DEFAULT_PORT


class CommandReader(Thread):
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """
            Provides singleton functionality. We only want one instance
            of this class in a process
        """
        with cls._lock:
            if CommandReader._instance is None:
                CommandReader._instance = super(CommandReader, cls).__new__(cls)
                CommandReader._instance._initialized = False
            return CommandReader._instance

    def __init__(self,
                 baudrate: int = DEFAULT_BAUDRATE,
                 port: str = DEFAULT_PORT) -> None:
        if self._initialized:
            return
        else:
            self._initialized = True
        super().__init__(name="PyLegacy Command Reader")
        # prep our consumer
        self._is_running = True
        self._cv = threading.Condition()
        self._deque = deque(maxlen=1024)
        self.start()
        # prep our producer
        from .serial_reader import SerialReader
        self._serial_reader_thread = SerialReader(baudrate, port, self)

    def run(self) -> None:
        while self._is_running:
            # process bytes, as long as there are any
            if not self._deque:
                self._cv.wait()  # wait to be notified
            # check if the first bite is in the list of allowable command prefixes
            if self._deque[0] in TMCC_FIRST_BYTE_TO_INTERPRETER and len(self._deque) >= 3:
                # at this point, we have some sort of command.
                print(hex(self._deque[0]))
            elif len(self._deque) < 3:
                continue  # wait for more bytes
            else:
                # pop this byte and continue; we either received unparsable input
                # or started receiving data mid-command
                self._deque.popleft()

    def offer(self, data: bytes) -> None:
        self._deque.extend(data)
        self._cv.notify()

    def shutdown(self) -> None:
        self._is_running = False
                    