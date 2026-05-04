import logging
logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod

import adafruit_tca9548a
from pymodbus.client import ModbusSerialClient

import anyio
import board

_I2C = "i2c"
_MODBUS = "MODBUS"

class Bus(ABC):
    def __init__(self):
        self.lock = anyio.Lock()

class BlinkaI2CBus(Bus):
    def __init__(self):
        self.wrapped_bus = board.I2C()
        self.multiplexers = {}
        logger.info("Blinka I2C bus initialized")
    
    def ensure_multiplexer(self, address: int) -> adafruit_tca9548a.TCA9548A:
        if address not in self.multiplexers:
            self.multiplexers[address] = adafruit_tca9548a.TCA9548A(self.wrapped_bus, address=address)
            logger.info(f"Initialized new I2C multiplexer at address {address}")
        return self.multiplexers[address]

class MODBUS(Bus):
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = 'N',
        stopbits: int = 1,
        timeout: float = 1.0
    ):
        super().__init__()
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout
        )
    
    def __getattr__(self, name):
        # Proxy all other method calls to the underlying client
        try:
            attr = getattr(self.client, name)
        except AttributeError:
            raise AttributeError(f"Neither this '{type(self).__name__}' object nor the wrapped '{type(self.client).__name__}' object has any attribute '{name}'")
        if callable(attr):
            def locked_method(*args, **kwargs):
                return attr(*args, **kwargs)
            return locked_method
        else:
            return attr
    
    async def connect(self):
        try:
            self.client.connect()
            logger.info("Connected to MODBUS client")
        except Exception as e:
            logger.error(f"Failed to connect to MODBUS client: {e}")
            raise e

    def close(self):
        self.client.close()
        logger.info("Closed MODBUS client connection")

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

async def busses():
    i2c_bus = BlinkaI2CBus()
    modbus = MODBUS()
    await modbus.connect()
    return {
        _I2C: i2c_bus,
        _MODBUS: modbus
    }