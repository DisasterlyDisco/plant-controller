from collections.abc import Coroutine
from typing import Any

from adafruit_seesaw.seesaw import Seesaw

from . import Sensor
from ..datapoint import Datapoint, Confidence, Measurement
from ..com_bus import BlinkaI2CBus, I2CInterface

class MultiplexedStemma(Sensor, I2CInterface):
    def __init__(
            self,
            parameter: str,
            bus: BlinkaI2CBus,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
            multiplexer_address: int,
            multiplexer_port: int,
            address: int,
            tbr: int
        ):
        self.parameter = parameter
        self.wrapped_sensor = Seesaw(
            bus.ensure_multiplexer(multiplexer_address)[multiplexer_port],
            addr=address
        )
        self.db_save_function = db_save_function
        self.confidence = Confidence(interval=0.5, level=0.95)
        self.time_between_reads = tbr

    async def read(self):
        await self.db_save_function(
            Measurement(
                parameter=self.parameter,
                value=self.process_raw_value(
                    self.wrapped_sensor.moisture_read()
                ),
                confidence=self.confidence,
                units="%"
            )
        )
    
    def process_raw_value(self, raw_value):
        # Current dummy tranformation
        # Replace with actual transform based on calibration data
        return raw_value / 1023 * 100
    
    def get_capabilities(self):
        return {
            self.parameter: {
                "units": "%",
                "confidence": str(self.confidence),
                "time between reads": str(self.time_between_reads) + " seconds"
             }
         }