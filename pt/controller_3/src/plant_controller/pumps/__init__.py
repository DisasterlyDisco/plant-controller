"""
Pump control modules for plant watering system.

This package provides pump implementations for various hardware configurations:

    - CS_IO404Pump: Generic pump using CS-IO404 relay module
    - CS_IO404Based_AD20P_1230E: AD20P-1230E pump via CS-IO404 relay
    - CS_IO404Relay: Direct relay control for the CS-IO404 module
"""

from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any

from ..com_bus import Bus
from ..datapoint import Datapoint


class Pump(ABC):
    """
    Abstract base class for pump implementations.

    All pump classes must inherit from this and implement the
    pumping_callback method for timed dosage delivery.
    """

    def __init__(
        self,
        bus: Bus,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        calibration_parameters: dict[str, Any],
        address: str
    ):
        """
        Initialize the pump.

        Args:
            bus: Communication bus (I2C or MODBUS)
            db_save_function: Async function to save watering events
            calibration_parameters: Dict with 'slope' (sec/ml) and 'offset' (sec)
            address: Device address on the bus
        """
        self.bus = bus
        self.db_save_function = db_save_function
        self.calibration_parameters = calibration_parameters
        self.address = address

    @abstractmethod
    async def pumping_callback(self, dosage: int):
        """
        Activate the pump to deliver the specified dosage.

        This method is called by the pump scheduler and must block
        until the pumping is complete to ensure accurate dosage.

        Args:
            dosage: Amount to pump in milliliters
        """
        pass


# Import implementations for easy access
from .cs_io404 import CS_IO404Relay, CS_IO404Pump, CS_IO404Based_AD20P_1230E

__all__ = [
    'Pump',
    'CS_IO404Relay',
    'CS_IO404Pump',
    'CS_IO404Based_AD20P_1230E'
]