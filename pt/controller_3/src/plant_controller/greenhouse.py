from collections.abc import Coroutine
import random
from typing import Any

from .com_bus import Bus, I2CInterface
from .database import DatabaseClient
from .datapoint import Confidence, Datapoint, Measurement
from .sensors import Sensor
from .unit import Unit

class Greenhouse(Unit):
    def __init__(self, db_client: DatabaseClient, i2c_bus: Bus):
        super().__init__(name="greenhouse", db_client=db_client)
        self.register_sensor(DummySHT45(bus=i2c_bus, db_save_function=self.db_save_function))
        self.register_sensor(DummyAS7341(bus=i2c_bus, db_save_function=self.db_save_function))

class DummySHT45(Sensor, I2CInterface):
    _I2C_ADDRESS = 0x44
    _READ_COMMAND = 0xFD

    def __init__(
            self,
            bus: Bus,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]]
        ):
        self.bus = bus
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
        _dummy = await self.bus.query(self._I2C_ADDRESS, self._READ_COMMAND)
        temperature, humidity = random.uniform(0, 100), random.uniform(0, 100)
        self.confidence = self.temperature_confidence
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
                    confidence=DummySHT45.humidity_confidence(temperature, humidity),
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

class DummyAS7341(Sensor, I2CInterface):
    def __init__(
            self,
            bus: Bus,
            db_save_function: Coroutine[Any, Datapoint | list[Datapoint]]
        ):
        self.bus = bus
        self.db_save_function = db_save_function
        self.time_between_reads = 15
        self.parameters = [
            "415nm",
            "445nm",
            "480nm",
            "515nm",
            "555nm",
            "590nm",
            "630nm",
            "680nm",
            "IR"
        ]
        self.units = "lux"

    async def read(self):
        _dummy = await self.bus.query("address", "command")
        for parameter in self.parameters:
            value = random.uniform(0, 100)
            await self.db_save_function(
            Measurement(
                parameter=parameter,
                value=value,
                confidence=None,
                units=self.units
            )
        )

    def get_capabilities(self):
        return {
            "415nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "445nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "480nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "515nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "555nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "590nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "630nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "680nm": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            },
            "IR": {
                "units": "lux",
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }