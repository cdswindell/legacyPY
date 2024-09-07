from .tmcc2_command import TMCC2Command
from ..constants import TMCCCommandScope, LEGACY_ROUTE_COMMAND, DEFAULT_BAUDRATE, DEFAULT_PORT, \
    LEGACY_EXTENDED_BLOCK_COMMAND_PREFIX


class RouteCmd(TMCC2Command):
    def __init__(self, route: int, baudrate: int = DEFAULT_BAUDRATE, port: str = DEFAULT_PORT) -> None:
        if route < 1 or route > 99:
            raise ValueError("Route must be between 1 and 99")
        super().__init__(TMCCCommandScope.ENGINE, route, baudrate, port)
        self._command = self._build_command()

    def _command_prefix(self) -> bytes:
        return LEGACY_EXTENDED_BLOCK_COMMAND_PREFIX.to_bytes(1, byteorder='big')

    def _build_command(self) -> bytes:
        return self.command_prefix + self._encode_address(LEGACY_ROUTE_COMMAND)
