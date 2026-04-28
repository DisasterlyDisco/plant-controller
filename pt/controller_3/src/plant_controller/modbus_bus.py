"""
MODBUS RTU Bus implementation for RS485 communication via CH341 USB-to-Serial driver.

This module provides an async MODBUS RTU client that interfaces with RS485 devices
through the CH341 USB-to-Serial converter. The CH341 driver (ch341.ko) must be
loaded on the system - it typically creates a /dev/ttyUSB* device node.

Driver installation (if needed on Raspberry Pi):
    sudo apt-get install linux-headers-$(uname -r)
    cd documentation/notes/extra_peripherals/usb_to_RS485_module/CH341SER_LINUX/driver
    make
    sudo insmod ch341.ko
    # Or for persistent loading:
    sudo cp ch341.ko /lib/modules/$(uname -r)/kernel/drivers/usb/serial/
    sudo depmod

The device should appear as /dev/ttyUSB0 (or similar) when connected.

Example usage:
    bus = ModbusBus(port='/dev/ttyUSB0', baudrate=9600)
    result = await bus.query(slave_id=1, register_address=0x0000, register_count=2)
"""

import anyio
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from .com_bus import Bus, MODBUSInterface


class ModbusBus(Bus):
    """
    Async MODBUS RTU bus implementation for RS485 communication.

    This class provides asynchronous access to MODBUS RTU devices connected via
    the CH341 USB-to-RS485 converter. It wraps the synchronous pymodbus library
    with async primitives using anyio.

    Attributes:
        port: Serial port device path (e.g., '/dev/ttyUSB0')
        baudrate: Communication speed (default: 9600)
        parity: Parity checking ('N', 'E', 'O') - default: 'N' (None)
        stopbits: Number of stop bits (default: 1)
        bytesize: Data byte size (default: 8)
        timeout: Read timeout in seconds (default: 1.0)
    """

    def __init__(
        self,
        port: str = '/dev/ttyUSB0',
        baudrate: int = 9600,
        parity: str = 'N',
        stopbits: int = 1,
        bytesize: int = 8,
        timeout: float = 1.0
    ):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout

        self._client: ModbusSerialClient | None = None
        self._connected = False

    async def connect(self) -> bool:
        """
        Establish connection to the MODBUS RTU device.

        Returns:
            True if connection successful, False otherwise.
        """
        async with self.lock:
            if self._connected:
                return True

            self._client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout
            )

            # Run blocking connect in thread
            self._connected = await anyio.to_thread.run_sync(
                self._client.connect
            )
            return self._connected

    async def disconnect(self) -> None:
        """Close the MODBUS connection."""
        async with self.lock:
            if self._client and self._connected:
                await anyio.to_thread.run_sync(self._client.close)
                self._connected = False
                self._client = None

    async def query(
        self,
        slave_id: int,
        register_address: int,
        register_count: int = 1,
        function_code: int = 0x03
    ) -> list[int] | int | None:
        """
        Perform a MODBUS read operation.

        This is the primary interface matching the Bus.query() signature.
        Automatically connects if not already connected.

        Args:
            slave_id: MODBUS slave/device ID (1-247)
            register_address: Starting register address (0x0000 - 0xFFFF)
            register_count: Number of registers to read (default: 1)
            function_code: MODBUS function code:
                - 0x01: Read Coils
                - 0x02: Read Discrete Inputs
                - 0x03: Read Holding Registers (default)
                - 0x04: Read Input Registers

        Returns:
            List of register values, single value if register_count=1,
            or None on error.

        Raises:
            ConnectionError: If cannot establish connection to device.
            ModbusException: On MODBUS protocol errors.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                raise ConnectionError(
                    f"Failed to connect to MODBUS device on {self.port}"
                )

        async with self.lock:
            try:
                if function_code == 0x01:
                    result = await anyio.to_thread.run_sync(
                        lambda: self._client.read_coils(
                            address=register_address,
                            count=register_count,
                            slave=slave_id
                        )
                    )
                elif function_code == 0x02:
                    result = await anyio.to_thread.run_sync(
                        lambda: self._client.read_discrete_inputs(
                            address=register_address,
                            count=register_count,
                            slave=slave_id
                        )
                    )
                elif function_code == 0x03:
                    result = await anyio.to_thread.run_sync(
                        lambda: self._client.read_holding_registers(
                            address=register_address,
                            count=register_count,
                            slave=slave_id
                        )
                    )
                elif function_code == 0x04:
                    result = await anyio.to_thread.run_sync(
                        lambda: self._client.read_input_registers(
                            address=register_address,
                            count=register_count,
                            slave=slave_id
                        )
                    )
                else:
                    raise ValueError(f"Unsupported function code: {function_code}")

                if result.isError():
                    raise ModbusException(f"MODBUS error response: {result}")

                # Extract values based on function code
                if function_code in (0x01, 0x02):
                    values = result.bits[:register_count]
                else:
                    values = result.registers

                # Return single value if only one register requested
                if register_count == 1 and len(values) == 1:
                    return values[0]
                return values

            except ModbusException:
                raise
            except Exception as e:
                raise ModbusException(f"MODBUS query failed: {e}") from e

    async def write_register(
        self,
        slave_id: int,
        register_address: int,
        value: int
    ) -> bool:
        """
        Write a single holding register.

        Args:
            slave_id: MODBUS slave/device ID
            register_address: Register address to write
            value: Value to write (0-65535)

        Returns:
            True if write successful, False otherwise.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                raise ConnectionError(
                    f"Failed to connect to MODBUS device on {self.port}"
                )

        async with self.lock:
            result = await anyio.to_thread.run_sync(
                lambda: self._client.write_register(
                    address=register_address,
                    value=value,
                    slave=slave_id
                )
            )
            return not result.isError()

    async def write_registers(
        self,
        slave_id: int,
        register_address: int,
        values: list[int]
    ) -> bool:
        """
        Write multiple holding registers.

        Args:
            slave_id: MODBUS slave/device ID
            register_address: Starting register address
            values: List of values to write

        Returns:
            True if write successful, False otherwise.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                raise ConnectionError(
                    f"Failed to connect to MODBUS device on {self.port}"
                )

        async with self.lock:
            result = await anyio.to_thread.run_sync(
                lambda: self._client.write_registers(
                    address=register_address,
                    values=values,
                    slave=slave_id
                )
            )
            return not result.isError()

    async def write_coil(
        self,
        slave_id: int,
        coil_address: int,
        value: bool
    ) -> bool:
        """
        Write a single coil (digital output).

        Args:
            slave_id: MODBUS slave/device ID
            coil_address: Coil address to write
            value: True (ON) or False (OFF)

        Returns:
            True if write successful, False otherwise.
        """
        if not self._connected:
            connected = await self.connect()
            if not connected:
                raise ConnectionError(
                    f"Failed to connect to MODBUS device on {self.port}"
                )

        async with self.lock:
            result = await anyio.to_thread.run_sync(
                lambda: self._client.write_coil(
                    address=coil_address,
                    value=value,
                    slave=slave_id
                )
            )
            return not result.isError()

    def is_connected(self) -> bool:
        """Check if the MODBUS connection is active."""
        return self._connected and self._client is not None

    def __repr__(self) -> str:
        return (
            f"ModbusBus(port={self.port}, baudrate={self.baudrate}, "
            f"connected={self._connected})"
        )


class ModbusBusInterface(MODBUSInterface):
    """
    Mixin interface for MODBUS RTU peripherals.

    Sensors and actuators using RS485/MODBUS should inherit from this
    class and implement bus_type() to integrate with the bus discovery
    system.

    Example:
        class DFRobotSoilSensor(Sensor, ModbusBusInterface):
            @staticmethod
            def bus_type() -> str:
                return "MODBUS"

            async def read(self):
                # Read from MODBUS holding register 0x0000
                raw = await self.bus.query(
                    slave_id=self.slave_id,
                    register_address=0x0000,
                    register_count=2
                )
                # Process raw data...
    """
    pass
