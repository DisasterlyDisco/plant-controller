from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any
import importlib

import anyio

from ..com_bus import Bus
from ..datapoint import Confidence, Datapoint

class Sensor(ABC):
    def __init__(
            self,
            parameter: str,
            bus: Bus,
            confidence: Confidence,
            units: str,
            time_between_reads: float,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]]
        ):
        self.parameter = parameter
        self.bus = bus
        self.confidence = confidence
        self.units = units
        self.time_between_reads = time_between_reads
        self.db_save_function = db_save_function

    @abstractmethod
    async def read(self):
        pass
    
    async def reading_loop(self):
        while True:
            await self.read()
            await anyio.sleep(self.time_between_reads)
    
    def get_capabilities(self):
        return {
            self.parameter: {
                "units": self.units,
                "confidence": str(self.confidence),
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }

def init_sensor(
        module_name: str,
        class_name: str,
        parameter: str,
        busses: dict[str, Bus],
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        sensor_kwargs: dict[Any]
    ) -> Sensor:
    sensor_module = importlib.import_module(__name__ + "." + module_name)
    sensor_class = getattr(sensor_module, class_name)
    return sensor_class(
        parameter=parameter,
        bus=busses[sensor_class.bus_type()],
        db_save_function=db_save_function,
        **sensor_kwargs
    )