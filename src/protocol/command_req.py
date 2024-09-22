from typing import Callable, Self

from .constants import DEFAULT_ADDRESS, DEFAULT_BAUDRATE, DEFAULT_PORT
from .tmcc2.tmcc2_constants import TMCC2Enum, TMCC2CommandPrefix
from .tmcc2.tmcc2_constants import TMCC2CommandDef

from .constants import CommandScope, CommandSyntax
from .command_def import CommandDef, CommandDefEnum
from .tmcc1.tmcc1_constants import TMCC1CommandDef, TMCC1_COMMAND_PREFIX, TMCC1Enum
from .tmcc1.tmcc1_constants import TMCC1CommandIdentifier, TMCC1RouteCommandDef, TMCC1_TRAIN_COMMAND_PURIFIER
from .tmcc1.tmcc1_constants import TMCC1_TRAIN_COMMAND_MODIFIER
from src.utils.validations import Validations
from ..comm.comm_buffer import CommBuffer


class CommandReq:
    @classmethod
    def build(cls,
              command: CommandDefEnum | None,
              address: int = DEFAULT_ADDRESS,
              data: int = 0,
              scope: CommandScope = None) -> Self:
        cls._vet_request(command, address, data, scope)
        # we have to do these imports here to avoid cyclic dependencies
        from .sequence.sequence_constants import SequenceCommandEnum
        from .tmcc2.tmcc2_param_constants import TMCC2ParameterEnum
        if isinstance(command, SequenceCommandEnum):
            from .sequence.sequence_req import SequenceReq
            return SequenceReq.build(command, address, data, scope)
        elif isinstance(command, TMCC2ParameterEnum):
            from .tmcc2.param_command_req import ParameterCommandReq
            return ParameterCommandReq.build(command, address, data, scope)
        return CommandReq(command, address, data, scope)

    @classmethod
    def send_request(cls,
                     command: CommandDefEnum,
                     address: int = DEFAULT_ADDRESS,
                     data: int = 0,
                     scope: CommandScope = None,
                     repeat: int = 1,
                     delay: float = 0,
                     baudrate: int = DEFAULT_BAUDRATE,
                     port: str = DEFAULT_PORT,
                     server: str = None
                     ) -> None:
        # build & queue
        req = cls.build(command, address, data, scope)
        cls._enqueue_command(req.as_bytes, repeat, delay, baudrate, port, server)

    @classmethod
    def build_action(cls,
                     command: CommandDefEnum | None,
                     address: int = DEFAULT_ADDRESS,
                     data: int = 0,
                     scope: CommandScope = None,
                     repeat: int = 1,
                     delay: float = 0,
                     baudrate: int = DEFAULT_BAUDRATE,
                     port: str = DEFAULT_PORT,
                     server: str = None
                     ) -> Callable:
        # build & return action function
        req = cls.build(command, address, data, scope)
        return req.as_action(repeat=repeat, delay=delay, baudrate=baudrate, port=port, server=server)

    @classmethod
    def _determine_first_byte(cls, command: CommandDef, scope: CommandScope) -> bytes:
        """
            Generalized command scopes, such as ENGINE, SWITCH, etc.,
            map to syntax-specific command identifiers defined
            for the TMCC1 and TMCC2 commands
        """
        # otherwise, we need to figure out if we're returning a
        # TMCC1-style or TMCC2-style command prefix
        if isinstance(command, TMCC1CommandDef):
            return TMCC1_COMMAND_PREFIX.to_bytes(1, byteorder='big')
        elif isinstance(command, TMCC2CommandDef):
            validated_scope = cls._validate_requested_scope(command, scope)
            return TMCC2CommandPrefix(validated_scope.name).as_bytes
        raise TypeError(f"Command type not recognized {command}")

    @classmethod
    def _vet_request(cls,
                     command: CommandDefEnum,
                     address: int,
                     data: int,
                     scope: CommandScope,
                     ) -> None:
        from .sequence.sequence_constants import SequenceCommandEnum
        if isinstance(command, TMCC1Enum):
            enum_class = TMCC1Enum
        elif isinstance(command, TMCC2Enum) or isinstance(command, SequenceCommandEnum):
            enum_class = TMCC2Enum
        else:
            raise TypeError(f"Command def not recognized: '{command}'")

        max_val = 99
        syntax = CommandSyntax.TMCC2 if enum_class == TMCC2Enum else CommandSyntax.TMCC1
        if syntax == CommandSyntax.TMCC1 and command == TMCC1RouteCommandDef.ROUTE:
            scope = TMCC1CommandIdentifier.ROUTE
            max_val = 31
        if scope is None:
            scope = command.scope
        Validations.validate_int(address, min_value=1, max_value=max_val, label=scope.name.capitalize())
        if data is not None:
            Validations.validate_int(data, label=scope.name.capitalize())

    @classmethod
    def _enqueue_command(cls,
                         cmd: bytes,
                         repeat: int,
                         delay: float,
                         baudrate: int,
                         port: str | int,
                         server: str | None,
                         buffer: CommBuffer = None) -> None:
        repeat = Validations.validate_int(repeat, min_value=1, label="repeat")
        delay = Validations.validate_float(delay, min_value=0, label="delay")
        # send command to comm buffer
        if buffer is None:
            buffer = CommBuffer.build(baudrate=baudrate, port=port, server=server)
        cumulative_delay = 0
        for _ in range(repeat):
            if delay > 0 and repeat == 1:
                cumulative_delay = delay
            buffer.enqueue_command(cmd, cumulative_delay)
            if repeat != 1 and delay > 0 and _ != repeat - 1:
                cumulative_delay += delay

    @staticmethod
    def _validate_requested_scope(command_def: CommandDef, request: CommandScope) -> CommandScope:
        if request in [CommandScope.ENGINE, CommandScope.TRAIN]:
            if command_def.scope in [CommandScope.ENGINE, CommandScope.TRAIN]:
                return request
        # otherwise, return the scope associated with the native command def
        return command_def.scope

    def __init__(self,
                 command_def_enum: CommandDefEnum,
                 address: int = DEFAULT_ADDRESS,
                 data: int = 0,
                 scope: CommandScope = None) -> None:
        self._command_def_enum = command_def_enum
        self._command_def: TMCC2CommandDef = command_def_enum.value  # read only; do not modify
        self._address = address
        self._data = data
        self._native_scope = self._command_def.scope
        self._scope = self._validate_requested_scope(self._command_def, scope)
        self._buffer: CommBuffer | None = None

        # save the command bits from the def, as we will be modifying them
        self._command_bits = self._command_def.bits

        # apply the given address and data
        self._apply_address()
        self._apply_data()

    def __repr__(self) -> str:
        return f"<{self._command_def_enum.name} 0x{self.bits:04x}: {self.num_data_bits} data bits>"

    @property
    def address(self) -> int:
        return self._address

    @address.setter
    def address(self, new_address: int) -> None:
        if new_address != self._address:
            self._address = new_address
            self._apply_address()

    @property
    def data(self) -> int:
        return self._data

    @data.setter
    def data(self, new_data: int) -> None:
        if new_data != self._data:
            self._data = new_data
            self._apply_data()

    @property
    def scope(self) -> CommandScope:
        return self._scope

    @property
    def native_scope(self) -> CommandScope:
        return self._native_scope

    @property
    def command_def(self) -> TMCC2CommandDef:
        return self._command_def

    @property
    def bits(self) -> int:
        return self._command_bits

    @property
    def is_data(self) -> bool:
        return self.command_def.num_data_bits != 0

    @property
    def num_data_bits(self) -> int:
        return self.command_def.num_data_bits

    @property
    def data_max(self) -> int:
        return self.command_def.data_max

    @property
    def data_min(self) -> int:
        return self.command_def.data_min

    @property
    def syntax(self) -> CommandSyntax:
        return self._command_def.syntax

    @property
    def is_tmcc1(self) -> bool:
        return self._command_def.is_tmcc1

    @property
    def is_tmcc2(self) -> bool:
        return self._command_def.is_tmcc2

    @property
    def identifier(self) -> int | None:
        return self.command_def.identifier

    def send(self,
             repeat: int = 1,
             delay: float = 0,
             baudrate: int = DEFAULT_BAUDRATE,
             port: str = DEFAULT_PORT,
             server: str = None
             ) -> None:
        self._enqueue_command(self.as_bytes, repeat, delay, baudrate, port, server)

    @property
    def as_bytes(self) -> bytes:
        if self.scope is None:
            first_byte = self.command_def.first_byte
        else:
            first_byte = self._determine_first_byte(self.command_def, self.scope)
        return first_byte + self._command_bits.to_bytes(2, byteorder='big')

    def as_action(self,
                  repeat: int = 1,
                  delay: float = 0,
                  baudrate: int = DEFAULT_BAUDRATE,
                  port: str = DEFAULT_PORT,
                  server: str = None
                  ) -> Callable:
        buffer = CommBuffer.build(baudrate=baudrate, port=port, server=server)

        def send_func(new_address: int = None, new_data: int = None) -> None:
            if new_address and new_address != self.address:
                self.address = new_address
            if self.num_data_bits and new_data and new_data != self.data:
                self.data = new_data
            self._enqueue_command(self.as_bytes,
                                  repeat=repeat,
                                  delay=delay,
                                  baudrate=baudrate,
                                  port=port,
                                  server=server,
                                  buffer=buffer)

        return send_func

    def _apply_address(self, new_address: int = None) -> int:
        if not self.command_def.is_addressable:  # HALT command
            return self._command_bits
        # reset existing address bits, if any
        self._command_bits &= self._command_def.address_mask
        # figure out which address we're using
        the_address = new_address if new_address and new_address > 0 else self._address
        if self.syntax == CommandSyntax.TMCC1:
            self._command_bits |= the_address << 7
            if self.scope == CommandScope.TRAIN and self.identifier == TMCC1CommandIdentifier.ENGINE:
                self._command_bits &= TMCC1_TRAIN_COMMAND_PURIFIER
                self._command_bits |= TMCC1_TRAIN_COMMAND_MODIFIER
        elif self.syntax == CommandSyntax.TMCC2:
            self._command_bits |= the_address << 9
        else:
            raise ValueError(f"Command syntax not recognized {self.syntax}")
        return self._command_bits

    def _apply_data(self, new_data: int = None) -> int:
        """
            For commands that take parameters, such as engine speed and brake level,
            apply the data bits to the command op bytes to form the complete byte
            set to send to the Lionel LCS SER2.
        """
        data = new_data if new_data is not None else self.data
        if self.num_data_bits and data is None:
            raise ValueError("Data is required")
        if self.num_data_bits == 0:
            return self.bits
        elif self.command_def.data_map:
            d_map = self.command_def.data_map
            if data in d_map:
                data = d_map[data]
            else:
                raise ValueError(f"Invalid data value: {data} (not in map)")
        elif data < self.command_def.data_min or data > self.command_def.data_max:
            raise ValueError(f"Invalid data value: {data} (not in range)")
        # sanitize data so we don't set bits we shouldn't
        data_bits = (2 ** self.num_data_bits - 1)
        filtered_data = data & data_bits
        if data != filtered_data:
            raise ValueError(f"Invalid data value: {data} (not in range)")
        # clear out old data
        self._command_bits &= 0xFFFF & ~data_bits
        # set new data
        self._command_bits |= data
        return self._command_bits
