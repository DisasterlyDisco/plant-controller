from . import Sensor
from ..datapoint import Datapoint, Confidence
from ..com_bus import Bus

class DummyStemma(Sensor):
    def __init__(
            self,
            parameter: str,
            bus: Bus,
            db_save_function: callable,
            address: str
        ):
        self.parameter = parameter
        self.bus = bus
        self.db_save_function = db_save_function
        self.confidence = Confidence(interval=0.5, level=0.95)
        self.address = address
        self.time_between_reads = 15
    
    async def read(self):
        _dummy = await self.bus.query(self.address, 0x00)
        value = 42
        confidence = self.confidence
        await self.db_save_function(
            Datapoint(
                parameter="moisture",
                value=value,
                confidence=confidence,
                units="%"
            )
        )

    @staticmethod
    def bus_type() -> str:
        return "i2c"
    
    def get_capabilities(self):
        return {
            "moisture": {
                "units": "%",
                "confidence": str(self.confidence),
                "time between reads": str(self.time_between_reads) + " seconds"
            }
        }