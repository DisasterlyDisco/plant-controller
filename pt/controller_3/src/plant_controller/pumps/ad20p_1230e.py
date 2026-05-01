import logging
logger = logging.getLogger(__name__)

from collections.abc import Coroutine
from typing import Any

import anyio

from . import Pump
from ..datapoint import Datapoint
from ..com_bus import MODBUS, MODBUSInterface

class CS_IO404_Based_AD20P_1230E(Pump, MODBUSInterface):
    def __init__(
        self,
        bus: MODBUS,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        calibration_parameters: dict[str, Any],
        relay_address: int,
        coil_number: int
    ):
        self.bus = bus
        self.db_save_function = db_save_function
        self.calibration_parameters = calibration_parameters
        self.relay_address = relay_address
        self.coil_number = coil_number

    def doseage_to_time(self, dosage: int) -> float:
        slope = self.calibration_parameters["slope"]
        offset = self.calibration_parameters["offset"]
        return slope * dosage + offset

    async def pumping_callback(self, dosage: int):
        pump_time = self.doseage_to_time(dosage)
        logger.info(f"Starting pump {self.relay_address}-{self.coil_number} for {pump_time} seconds, corresponding to a dosage of {dosage} ml")
        await self.bus.write_coil(
            address=self.coil_number,
            value=True,
            device_id=self.relay_address
        )
        await anyio.sleep(pump_time)
        await self.bus.write_coil(
            address=self.coil_number,
            value=False,
            device_id=self.relay_address
        )
        logger.info(f"Stopped pump {self.relay_address}-{self.coil_number}")