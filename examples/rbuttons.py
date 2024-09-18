from src.gpio.gpio_handler import GpioHandler
from src.protocol.command_req import CommandReq
from src.protocol.tmcc1.tmcc1_constants import TMCC1AuxCommandDef
from src.protocol.tmcc2.tmcc2_constants import TMCC2RouteCommandDef
from src.protocol.tmcc2.tmcc2_constants import TMCC2EngineCommandDef

"""
    Simple examples of how to associate Lionel commands to Raspberry Pi buttons
"""
DEFAULT_SERVER = "192.168.3.61"

GpioHandler.when_button_held(26, TMCC2EngineCommandDef.BLOW_HORN_ONE, server=DEFAULT_SERVER)

GpioHandler.when_button_pressed(21, TMCC2RouteCommandDef.ROUTE, 10, server=DEFAULT_SERVER)

off = CommandReq(TMCC1AuxCommandDef.AUX2_OPTION_ONE, 9)
on = CommandReq(TMCC1AuxCommandDef.AUX1_OPTION_ONE, 9)
GpioHandler.when_toggle_switch(13, 19, off, on, led_pin=20, server=DEFAULT_SERVER)
# GpioHandler.when_toggle_button_pressed(19,  on, led_pin=20, server=DEFAULT_SERVER)

GpioHandler.when_pot(TMCC2EngineCommandDef.ABSOLUTE_SPEED, 88, server=DEFAULT_SERVER)

print("Buttons registered...")
