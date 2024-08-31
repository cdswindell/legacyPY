from .command_base import CommandBase
from .constants import TMCC1_COMMAND_PREFIX
from .constants import TMCC1_ROUTE_COMMAND
from .constants import LEGACY_EXTENDED_BLOCK_COMMAND_PREFIX
from .constants import LEGACY_EXTENDED_ROUTE_COMMAND


class RouteCmd(CommandBase):
    def __init__(self, route: int, baudrate: int = 9600, port: str = "/dev/ttyUSB0") -> None:
        CommandBase.__init__(self, baudrate, port)
        if route < 1 or route > 99:
            raise ValueError("Route must be between 1 and 99")
        self._route = route

    def fire(self) -> None:
        if self._route < 10:
            cmd = (TMCC1_COMMAND_PREFIX.to_bytes(1, 'big') +
                   ((self._route << 7) | TMCC1_ROUTE_COMMAND).to_bytes(2, 'big'))
        else:
            cmd = (LEGACY_EXTENDED_BLOCK_COMMAND_PREFIX.to_bytes(1, 'big') +
                   ((self._route << 9) | LEGACY_EXTENDED_ROUTE_COMMAND).to_bytes(2, 'big'))

        # cue the command to send to the LCS SER2
        self.queue_cmd(cmd)
