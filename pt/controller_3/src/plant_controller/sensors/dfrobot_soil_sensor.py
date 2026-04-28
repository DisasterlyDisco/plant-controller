"""
DFRobot RS485 Soil Sensor driver.

This sensor provides soil temperature, humidity, and electrical conductivity (EC)
measurements over RS485/MODBUS RTU.

Typical wiring for the sensor:
    Red    -> VCC (9-24V DC)
    Black  -> GND
    Yellow -> RS485 A (D+)
    White  -> RS485 B (D-)

The sensor uses default MODBUS settings:
    - Baudrate: 9600
    - Data bits: 8
    - Stop bits: 1
    - Parity: None
    - Slave ID: 1 (configurable)

Register map (example - consult datasheet for your specific sensor model):
    0x0000: Soil Temperature (x10, °C)
    0x0001: Soil Humidity (x10, %)
    0x0002: Soil EC (raw value, μS/cm)
"""

from collections.abc import Coroutine
from typing import Any

from . import Sensor
from ..datapoint import Datapoint, Confidence, Measurement
from ..com_bus import Bus
from ..modbus_bus import ModbusBusInterface


class DFRobotSoilSensor(Sensor, ModbusBusInterface):
    """
    DFRobot RS485/MODBUS Soil Sensor implementation.

    Reads soil temperature, humidity, and EC from a DFRobot RS485
    soil sensor connected via MODBUS RTU.

    Attributes:
        slave_id: MODBUS slave ID of the sensor (default: 1)
        temp_register: Register address for temperature reading
        humidity_register: Register address for humidity reading
        ec_register: Register address for EC reading
    """

    # Default register addresses for DFRobot soil sensor
    DEFAULT_TEMP_REGISTER = 0x0000
    DEFAULT_HUMIDITY_REGISTER = 0x0001
    DEFAULT_EC_REGISTER = 0x0002

    def __init__(
        self,
        parameter: str,
        bus: Bus,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        slave_id: int = 1,
        tbr: int = 60,
        temp_register: int = DEFAULT_TEMP_REGISTER,
        humidity_register: int = DEFAULT_HUMIDITY_REGISTER,
        ec_register: int = DEFAULT_EC_REGISTER
    ):
        """
        Initialize the DFRobot soil sensor.

        Args:
            parameter: The parameter being measured ('temperature', 'humidity', 'ec')
            bus: The MODBUS bus instance
            db_save_function: Async function to save datapoints to database
            slave_id: MODBUS slave ID (default: 1)
            tbr: Time between reads in seconds (default: 60)
            temp_register: Register address for temperature
            humidity_register: Register address for humidity
            ec_register: Register address for EC
        """
        self.parameter = parameter
        self.bus = bus
        self.db_save_function = db_save_function
        self.slave_id = slave_id
        self.time_between_reads = tbr
        self.temp_register = temp_register
        self.humidity_register = humidity_register
        self.ec_register = ec_register

        # Confidence intervals based on sensor datasheet
        # These should be calibrated for your specific sensor
        self._confidences = {
            'temperature': Confidence(interval=0.5, level=0.95),  # ±0.5°C
            'humidity': Confidence(interval=3.0, level=0.95),     # ±3%
            'ec': Confidence(interval=5.0, level=0.95)            # ±5%
        }

    @property
    def confidence(self) -> Confidence:
        """Get the confidence interval for the current parameter."""
        return self._confidences.get(
            self.parameter,
            Confidence(interval=1.0, level=0.95)
        )

    @property
    def units(self) -> str:
        """Get the measurement units for the current parameter."""
        unit_map = {
            'temperature': '°C',
            'humidity': '%',
            'ec': 'μS/cm'
        }
        return unit_map.get(self.parameter, 'unknown')

    async def read(self):
        """
        Read the configured parameter from the sensor.

        Reads the appropriate register based on the configured parameter
        and saves the measurement to the database.
        """
        # Select register based on parameter
        register_map = {
            'temperature': self.temp_register,
            'humidity': self.humidity_register,
            'ec': self.ec_register
        }

        register = register_map.get(self.parameter)
        if register is None:
            raise ValueError(f"Unknown parameter: {self.parameter}")

        # Read from MODBUS
        raw_value = await self.bus.query(
            slave_id=self.slave_id,
            register_address=register,
            register_count=1,
            function_code=0x03  # Read holding registers
        )

        # Convert raw value based on parameter type
        # DFRobot sensors typically return values x10 for temperature/humidity
        if self.parameter in ('temperature', 'humidity'):
            value = raw_value / 10.0
        else:
            value = float(raw_value)

        # Create and save measurement
        measurement = Measurement(
            parameter=self.parameter,
            value=value,
            confidence=self.confidence,
            units=self.units
        )

        await self.db_save_function(measurement)

    def get_capabilities(self):
        """Return the capabilities of this sensor."""
        return {
            self.parameter: {
                'units': self.units,
                'confidence': str(self.confidence),
                'time between reads': f'{self.time_between_reads} seconds',
                'slave_id': self.slave_id,
                'register': getattr(self, f'{self.parameter}_register')
            }
        }


class DFRobotSoilSensorMulti(Sensor, ModbusBusInterface):
    """
    Multi-parameter DFRobot soil sensor that reads all values in one call.

    This variant reads temperature, humidity, and EC in a single MODBUS
    transaction for efficiency, saving all three measurements to the database.
    """

    def __init__(
        self,
        parameter: str,  # Ignored - reads all parameters
        bus: Bus,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        slave_id: int = 1,
        tbr: int = 60,
        base_register: int = 0x0000
    ):
        self.parameter = 'multi'  # Override
        self.bus = bus
        self.db_save_function = db_save_function
        self.slave_id = slave_id
        self.time_between_reads = tbr
        self.base_register = base_register

        self.confidence = Confidence(interval=1.0, level=0.95)
        self.units = 'mixed'

    async def read(self):
        """Read all three parameters from consecutive registers."""
        # Read 3 consecutive registers: temp, humidity, EC
        values = await self.bus.query(
            slave_id=self.slave_id,
            register_address=self.base_register,
            register_count=3,
            function_code=0x03
        )

        if not isinstance(values, list) or len(values) != 3:
            raise RuntimeError(f"Expected 3 register values, got: {values}")

        temp_raw, humidity_raw, ec_raw = values

        # Create measurements for all three parameters
        measurements = [
            Measurement(
                parameter='soil_temperature',
                value=temp_raw / 10.0,
                confidence=Confidence(interval=0.5, level=0.95),
                units='°C'
            ),
            Measurement(
                parameter='soil_humidity',
                value=humidity_raw / 10.0,
                confidence=Confidence(interval=3.0, level=0.95),
                units='%'
            ),
            Measurement(
                parameter='soil_ec',
                value=float(ec_raw),
                confidence=Confidence(interval=5.0, level=0.95),
                units='μS/cm'
            )
        ]

        await self.db_save_function(measurements)

    def get_capabilities(self):
        """Return the capabilities of this multi-sensor."""
        return {
            'soil_temperature': {
                'units': '°C',
                'confidence': '±0.5°C at 95% confidence',
                'time between reads': f'{self.time_between_reads} seconds'
            },
            'soil_humidity': {
                'units': '%',
                'confidence': '±3% at 95% confidence',
                'time between reads': f'{self.time_between_reads} seconds'
            },
            'soil_ec': {
                'units': 'μS/cm',
                'confidence': '±5 μS/cm at 95% confidence',
                'time between reads': f'{self.time_between_reads} seconds'
            }
        }
