from abc import ABC, abstractmethod
import random

import anyio

_I2C = "i2c"
_MODBUS = "MODBUS"

# Import ModbusBus for re-export (avoid circular imports)
__all__ = [
    'Bus', 'DummmyI2CBus', 'DummyMODBUS', 'BusInterface',
    'I2CInterface', 'MODBUSInterface', 'busses', 'ModbusBus'
]

class Bus(ABC):
    def __init__(self):
        self.lock = anyio.Lock()
    
    @abstractmethod
    async def query(self, *args):
        pass

class DummmyI2CBus(Bus):
    async def query(self, *args):
        async with self.lock:
            await anyio.sleep(0.001)
            return random.uniform(0, 100)

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

def busses(use_real_modbus: bool = False, **modbus_kwargs) -> dict[str, Bus]:
    """
    Create and return the default bus instances for the controller.

    Args:
        use_real_modbus: If True, use real ModbusBus instead of DummyMODBUS.
                         Requires the CH341 driver to be loaded and device connected.
        **modbus_kwargs: Additional arguments passed to ModbusBus if using real modbus.
                         Common options:
                         - port: Serial port (default: '/dev/ttyUSB0')
                         - baudrate: Baud rate (default: 9600)
                         - parity: Parity ('N', 'E', 'O') (default: 'N')
                         - timeout: Read timeout in seconds (default: 1.0)

    Returns:
        Dictionary mapping bus type names to Bus instances.

    Example:
        # Using dummy MODBUS for testing
        busses = busses()

        # Using real MODBUS with default settings
        busses = busses(use_real_modbus=True)

        # Using real MODBUS with custom settings
        busses = busses(
            use_real_modbus=True,
            port='/dev/ttyUSB1',
            baudrate=115200
        )
    """
    from .modbus_bus import ModbusBus

    modbus_bus = ModbusBus(**modbus_kwargs) if use_real_modbus else DummyMODBUS()

    return {
        _I2C: DummmyI2CBus(),
        _MODBUS: modbus_bus
    }


# Import ModbusBus at end to avoid circular import issues
from .modbus_bus import ModbusBus  # noqa: E402, F401