from collections.abc import Coroutine
import math
import random
import statistics
from typing import Any

from . import Sensor
from ..datapoint import Datapoint, Confidence, Measurement
from ..com_bus import Bus, I2CInterface

class DummyStemma(Sensor, I2CInterface):
    def __init__(
            self,
            parameter: str,
            bus: Bus,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
            address: str,
            tbr: int
        ):
        self.parameter = parameter
        self.bus = bus
        self.db_save_function = db_save_function
        self.confidence = Confidence(interval=0.5, level=0.95)
        self.address = address
        self.time_between_reads = tbr

    async def read(self):
        _dummy = await self.bus.query(self.address, 0x00)
        value = 42
        confidence = self.confidence
        await self.db_save_function(
            Measurement(
                parameter=self.parameter,
                value=value,
                confidence=confidence,
                units="%"
            )
        )
    
    def get_capabilities(self):
        return {
            self.parameter: {
                "units": "%",
                "confidence": str(self.confidence),
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }
    
class DummyStemmaDugtrio(Sensor, I2CInterface):
    def __init__(
            self,
            parameter: str,
            bus: Bus,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
            addresses: list[str],
            tbr: int
        ):
        if len(addresses) < 1:
            raise ValueError("'addresses' must include at least one address")
        self.parameter = parameter
        self.bus = bus
        self.db_save_function = db_save_function
        self.confidence = Confidence(interval=0.5, level=0.95)
        self.addresses = addresses
        self.time_between_reads = tbr
    
    async def read(self):
        values = []
        for address in self.addresses:
            _dummy = await self.bus.query(address, 0x00)
            values.append(random.uniform(0, 100))
        mean = statistics.fmean(values)
        std_div = statistics.stdev(values)
        conf_int = 2*std_div/math.sqrt(len(values))
        await self.db_save_function(
            Measurement(
                parameter=self.parameter,
                value=mean,
                confidence=Confidence(conf_int, 0.95),
                units="%"
            )
        )
    
    def get_capabilities(self):
        return {
            self.parameter: {
                "units": "%",
                "confidence": "Variable, measurement dependent",
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }