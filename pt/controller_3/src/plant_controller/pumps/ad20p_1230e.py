import time
import datetime

from . import Pump
from ..com_bus import MODBUSInterface
from ..datapoint import WateringEvent

class CS_IO404_Based_AD20P_1230E(Pump, MODBUSInterface):
    async def pumping_callback(self, dosage: int):
        print(f"PUMPING {dosage} ml!")
        pumping_time = (
            dosage
            * self.calibration_parameters["slope"]
            + self.calibration_parameters["offset"]
        )
        _dummy = await self.bus.query(self.address, 0x00)

        print(f"Gonna be PUMPING for {pumping_time} seconds!")
        print(f"Starting at {datetime.datetime.now()}")
        time.sleep(pumping_time)
        print(f"Ended at {datetime.datetime.now()}")

        await self.db_save_function(
            WateringEvent(dosage)
        )
