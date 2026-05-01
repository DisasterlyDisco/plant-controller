from abc import ABC, abstractmethod
import random

import adafruit_tca9548a

import anyio
import board

_I2C = "i2c"
_MODBUS = "MODBUS"

class Bus(ABC):
    def __init__(self):
        self.lock = anyio.Lock()

class BlinkaI2CBus:
    def __init__(self):
        self.wrapped_bus = board.I2C()
        self.multiplexers = {}
    
    def ensure_multiplexer(self, address: int) -> adafruit_tca9548a.TCA9548A:
        if address not in self.multiplexers:
            self.multiplexers[address] = adafruit_tca9548a.TCA9548A(self.wrapped_bus, address=address)
        return self.multiplexers[address]

class DummyMODBUS(Bus):
    async def query(self, *args):
        async with self.lock:
            await anyio.sleep(0.001)
            return random.uniform(0, 100)

class BusInterface(ABC):
    @staticmethod
    @abstractmethod
    def bus_type() -> str:
        """
        Must return the string name of the bustype that this
        peripheral uses.

        Returns:
            (str): The canonical string for the bus type.
        """
        pass

class I2CInterface(BusInterface):
    @staticmethod
    def bus_type() -> str:
        """
        Signifies that the implementer of this interface uses the i2c bus protocol.

        Returns:
            (str): The canoncical string for the i2c bus.
        """
        return _I2C


class MODBUSInterface(BusInterface):
    @staticmethod
    def bus_type() -> str:
        """
        Signifies that the implementer of this interface uses the i2c bus protocol.

        Returns:
            (str): The canoncical string for MODBUS.
        """
        return _MODBUS

busses = {
    _I2C: BlinkaI2CBus(),
    _MODBUS: DummyMODBUS()
}