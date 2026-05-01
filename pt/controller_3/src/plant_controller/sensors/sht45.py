from collections.abc import Coroutine
from typing import Any

import adafruit_sht4x

from . import Sensor
from ..datapoint import Datapoint, Confidence, Measurement
from ..com_bus import BlinkaI2CBus, I2CInterface

class GreenhouseSHT45(Sensor, I2CInterface):
    def __init__(
        self,
        bus: BlinkaI2CBus,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        **kwargs: Any
    ):
        self.wrapped_sensor = adafruit_sht4x.SHT4x(bus.wrapped_bus)
        self.wrapped_sensor.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
        self.db_save_function = db_save_function
        self.time_between_reads=15
        self.temperature_confidence = Confidence(interval=0.2, level=0.95)

    @staticmethod
    def humidity_confidence(temperature, humidity):
        if humidity > 95:
            return Confidence(interval=1.75, level=0.95)
        elif humidity > 75 or humidity < 15 or temperature > 55 or temperature < 15:
            return Confidence(interval=1.5, level=0.95)
        else:
            return Confidence(interval=1, level=0.95)

    async def read(self):
        temperature, humidity = self.wrapped_sensor.measurements
        await self.db_save_function(
            [
                Measurement(
                    parameter="temperature",
                    value=temperature,
                    confidence=self.temperature_confidence,
                    units="°C"
                ),
                Measurement(
                    parameter="humidity",
                    value=humidity,
                    confidence=GreenhouseSHT45.humidity_confidence(temperature, humidity),
                    units="%"
                )
            ]
        )

    def get_capabilities(self):
        return {
            "temperature": {
                "units": "°C",
                "confidence": str(self.temperature_confidence),
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "humidity": {
                "units": "%",
                "confidence": "Varies based on temperature and humidity",
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }
