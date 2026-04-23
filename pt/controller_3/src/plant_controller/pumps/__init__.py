from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any

from ..com_bus import Bus
from ..datapoint import Datapoint

class Pump(ABC):
    def __init__(
            self,
            bus: Bus,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
            calibration_parameters: dict[str, Any],
            address: str
        ):
        self.bus = bus
        self.db_save_function = db_save_function
        self.calibration_parameters = calibration_parameters
        self.address = address

    @abstractmethod
    async def pumping_callback(self, dosage: int):
        """
        Passed to the pumps schedule, to be called whenever this pump should activate.

        Make sure to have the pump block when doing the pumping to ensure correct dosage.

        :param dosage: The amount to pump in milliliters
        :type dosage: int
        """
        pass