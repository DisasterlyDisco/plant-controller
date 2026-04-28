"""
CS-IO404 MODBUS RTU Relay Module driver.

The CS-IO404 is a 4-channel relay output / 4-channel digital input module
that communicates via RS485/MODBUS RTU.

Typical wiring:
    VCC    -> 9-24V DC
    GND    -> Ground
    A+     -> RS485 A (D+)
    B-     -> RS485 B (D-)

Default MODBUS settings:
    - Baudrate: 9600
    - Data bits: 8
    - Stop bits: 1
    - Parity: None
    - Slave ID: 1 (configurable via DIP switches or registers)

Register map for CS-IO404:
    Coils (0x01/0x05 functions):
        0x0000: Relay 1 output
        0x0001: Relay 2 output
        0x0002: Relay 3 output
        0x0003: Relay 4 output

    Discrete Inputs (0x02 function):
        0x0000: Input 1 state
        0x0001: Input 2 state
        0x0002: Input 3 state
        0x0003: Input 4 state

    Holding Registers (0x03/0x06/0x10 functions):
        0x0000: Device address (slave ID)
        0x0001: Baud rate configuration
        0x0002: Relay delay time (for pulsed operation)
"""

import datetime
from collections.abc import Coroutine
from typing import Any

import anyio

from . import Pump
from ..com_bus import Bus
from ..datapoint import Datapoint, WateringEvent
from ..modbus_bus import ModbusBusInterface


class CS_IO404Relay:
    """
    Interface to the CS-IO404 4-channel relay module.

    This class provides direct control over the relay outputs and
    can read the digital inputs of the CS-IO404 module.
    """

    # Coil addresses for relays (0-indexed)
    RELAY_1 = 0x0000
    RELAY_2 = 0x0001
    RELAY_3 = 0x0002
    RELAY_4 = 0x0003

    # Input addresses
    INPUT_1 = 0x0000
    INPUT_2 = 0x0001
    INPUT_3 = 0x0002
    INPUT_4 = 0x0003

    def __init__(
        self,
        bus: Bus,
        slave_id: int = 1
    ):
        """
        Initialize the CS-IO404 relay interface.

        Args:
            bus: The MODBUS bus instance
            slave_id: MODBUS slave ID of the relay module (default: 1)
        """
        self.bus = bus
        self.slave_id = slave_id

    async def set_relay(self, relay: int, state: bool) -> bool:
        """
        Set a single relay to ON or OFF.

        Args:
            relay: Relay number (0-3) or coil address (0x0000-0x0003)
            state: True for ON, False for OFF

        Returns:
            True if command was accepted, False otherwise
        """
        # Handle relay number (0-3) or coil address
        if relay in (0, 1, 2, 3):
            coil_address = relay
        elif relay in (self.RELAY_1, self.RELAY_2, self.RELAY_3, self.RELAY_4):
            coil_address = relay
        else:
            raise ValueError(f"Invalid relay: {relay}. Use 0-3 or RELAY_* constants.")

        return await self.bus.write_coil(
            slave_id=self.slave_id,
            coil_address=coil_address,
            value=state
        )

    async def set_relay_on(self, relay: int) -> bool:
        """Turn a relay ON."""
        return await self.set_relay(relay, True)

    async def set_relay_off(self, relay: int) -> bool:
        """Turn a relay OFF."""
        return await self.set_relay(relay, False)

    async def pulse_relay(self, relay: int, duration_ms: int) -> bool:
        """
        Pulse a relay ON for a specified duration then OFF.

        Args:
            relay: Relay number (0-3)
            duration_ms: Duration to keep relay ON in milliseconds

        Returns:
            True if operation completed successfully
        """
        success = await self.set_relay_on(relay)
        if not success:
            return False

        await anyio.sleep(duration_ms / 1000.0)
        return await self.set_relay_off(relay)

    async def get_relay_states(self) -> list[bool]:
        """
        Read the current state of all relays.

        Returns:
            List of 4 boolean values representing relay states
        """
        result = await self.bus.query(
            slave_id=self.slave_id,
            register_address=0x0000,
            register_count=4,
            function_code=0x01  # Read coils
        )

        if isinstance(result, list):
            return result
        return [result]

    async def get_input_states(self) -> list[bool]:
        """
        Read the current state of all digital inputs.

        Returns:
            List of 4 boolean values representing input states
        """
        result = await self.bus.query(
            slave_id=self.slave_id,
            register_address=0x0000,
            register_count=4,
            function_code=0x02  # Read discrete inputs
        )

        if isinstance(result, list):
            return result
        return [result]

    async def get_relay_config(self) -> dict[str, Any]:
        """
        Read the relay module configuration.

        Returns:
            Dictionary with device address and baud rate settings
        """
        registers = await self.bus.query(
            slave_id=self.slave_id,
            register_address=0x0000,
            register_count=3,
            function_code=0x03  # Read holding registers
        )

        baud_map = {
            0: 2400,
            1: 4800,
            2: 9600,
            3: 19200,
            4: 38400
        }

        return {
            'slave_id': registers[0],
            'baud_rate': baud_map.get(registers[1], 'unknown'),
            'relay_delay': registers[2]
        }


class CS_IO404Pump(Pump, ModbusBusInterface):
    """
    Pump implementation using CS-IO404 relay module.

    Controls a pump connected to one of the CS-IO404 relay outputs.
    The pump is activated by turning the relay ON for a calculated
    duration based on calibration parameters.

    Calibration parameters should include:
        - 'slope': seconds per ml (flow rate)
        - 'offset': base activation time in seconds
        - 'relay': which relay output to use (0-3)
    """

    @staticmethod
    def bus_type() -> str:
        """Returns MODBUS as the bus type."""
        return "MODBUS"

    async def pumping_callback(self, dosage: int):
        """
        Pump a specific dosage in milliliters.

        Args:
            dosage: Amount to pump in milliliters
        """
        # Extract calibration parameters
        slope = self.calibration_parameters.get("slope", 0.1)  # seconds/ml
        offset = self.calibration_parameters.get("offset", 0.5)  # seconds
        relay = self.calibration_parameters.get("relay", 0)  # relay 0-3

        # Calculate pumping time
        pumping_time = dosage * slope + offset

        print(f"[CS-IO404 Pump] Pumping {dosage}ml using relay {relay}")
        print(f"[CS-IO404 Pump] Duration: {pumping_time:.2f}s")
        print(f"[CS-IO404 Pump] Start: {datetime.datetime.now()}")

        # Create relay controller
        relay_ctrl = CS_IO404Relay(bus=self.bus, slave_id=int(self.address))

        # Turn relay ON
        success = await relay_ctrl.set_relay_on(relay)
        if not success:
            raise RuntimeError(f"Failed to activate relay {relay}")

        # Wait for calculated duration
        await anyio.sleep(pumping_time)

        # Turn relay OFF
        success = await relay_ctrl.set_relay_off(relay)
        if not success:
            raise RuntimeError(f"Failed to deactivate relay {relay}")

        print(f"[CS-IO404 Pump] End: {datetime.datetime.now()}")

        # Record the watering event
        await self.db_save_function(WateringEvent(dosage))


class CS_IO404Based_AD20P_1230E(Pump, ModbusBusInterface):
    """
    Updated pump implementation for AD20P-1230E pumps using CS-IO404.

    This replaces the dummy implementation with actual MODBUS coil control.
    """

    @staticmethod
    def bus_type() -> str:
        """Returns MODBUS as the bus type."""
        return "MODBUS"

    async def pumping_callback(self, dosage: int):
        """
        Pump a specific dosage using calibrated timing.

        Args:
            dosage: Amount to pump in milliliters
        """
        # Calculate pumping time from calibration
        slope = self.calibration_parameters.get("slope", 0.0417)  # ~240L/hr pump
        offset = self.calibration_parameters.get("offset", 0.5)
        pumping_time = dosage * slope + offset

        print(f"[AD20P-1230E] Pumping {dosage}ml via CS-IO404")
        print(f"[AD20P-1230E] Duration: {pumping_time:.2f}s")
        print(f"[AD20P-1230E] Start: {datetime.datetime.now()}")

        # Control relay via MODBUS
        relay_ctrl = CS_IO404Relay(bus=self.bus, slave_id=int(self.address))
        relay = self.calibration_parameters.get("relay", 0)

        # Pulse the relay for the calculated duration
        success = await relay_ctrl.pulse_relay(
            relay=relay,
            duration_ms=int(pumping_time * 1000)
        )

        if not success:
            raise RuntimeError("Failed to complete pump operation")

        print(f"[AD20P-1230E] End: {datetime.datetime.now()}")

        # Record the watering event
        await self.db_save_function(WateringEvent(dosage))
