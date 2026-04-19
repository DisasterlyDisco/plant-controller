from abc import ABC, abstractmethod
import anyio
from .datapoint import Confidence

class Sensor(ABC):
    def __init__(
            self,
            parameter: str,
            bus,
            confidence: Confidence,
            units: str,
            time_between_reads: float,
            db_save_function: callable
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