"""
Sensor modules for plant monitoring system.

Modules in this package should implement the Sensor or SyncSensor abstract base
classes defined here, which specify the required interface for all sensors in
the system.

Sensors classes in submodules are dynamically loaded and initialized by the
controller based on configuration files.
"""

from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any
import importlib

import anyio

from ..com_bus import Bus
from ..datapoint import Confidence, Datapoint


class Sensor(ABC):
    """
    Abstract base class for sensor implementations.

    All sensor classes must inherit from this and implement the
    read method for taking measurements.
    """

    def __init__(
        self,
        parameter: str,
        bus: Bus,
        confidence: Confidence,
        units: str,
        time_between_reads: float,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]]
    ):
        """
        Initialize the sensor.

        Args:
            parameter: Name of the measured parameter (e.g., 'temperature')
            bus: Communication bus instance
            confidence: Measurement confidence interval
            units: Unit of measurement (e.g., '°C', '%')
            time_between_reads: Seconds between automatic readings
            db_save_function: Async function to save measurements
        """
        self.parameter = parameter
        self.bus = bus
        self.confidence = confidence
        self.units = units
        self.time_between_reads = time_between_reads
        self.db_save_function = db_save_function

    @abstractmethod
    async def read(self):
        """Take a measurement and save it via db_save_function."""
        pass

    async def reading_loop(self):
        """Continuous reading loop - call via anyio task group."""
        while True:
            await self.read()
            await anyio.sleep(self.time_between_reads)

    def get_capabilities(self):
        """Return sensor capabilities dict."""
        return {
            self.parameter: {
                "units": self.units,
                "confidence": str(self.confidence),
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }

class SyncSensor(Sensor):
    """
    Sensor subclass for devices that require synchronous reads (e.g., Blinka-based I2C sensors).

    Inheritors of this class must implement the synced_read method.
    """

    @abstractmethod
    def synced_read(self):
        """Synchronous method to take a measurement."""
        pass

    async def read(self):
        """Async wrapper that calls the synchronous read method."""
        return self.synced_read()


def init_sensor(
    module_name: str,
    class_name: str,
    parameter: str,
    busses: dict[str, Bus],
    db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
    sensor_kwargs: dict[Any] = {}
) -> Sensor:
    """
    Dynamically initialize a sensor from a module.

    Args:
        module_name: Name of the module containing the sensor class
        class_name: Name of the sensor class
        parameter: Parameter being measured
        busses: Dictionary of available bus instances
        db_save_function: Function to save datapoints
        sensor_kwargs: Additional kwargs passed to sensor constructor

    Returns:
        Initialized Sensor instance
    """
    sensor_module = importlib.import_module(__name__ + "." + module_name)
    sensor_class = getattr(sensor_module, class_name)
    return sensor_class(
        parameter=parameter,
        bus=busses[sensor_class.bus_type()],
        db_save_function=db_save_function,
        **sensor_kwargs
    )