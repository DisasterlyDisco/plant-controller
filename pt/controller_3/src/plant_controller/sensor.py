from abc import ABC, abstractmethod
import anyio
from anyio import Lock, create_task_group
from .database import DatabaseClient
from .datapoint import Datapoint, Confidence

import random

class Sensor(ABC):
    def __init__(
            self,
            parameter: str,
            bus,
            confidence: Confidence,
            units: str,
            time_between_reads: float,
            db_save_function: callable | None = None
        ):
        self.parameter = parameter
        self.bus = bus
        self.confidence = confidence
        self.units = units
        self.time_between_reads = time_between_reads
        self.db_save_function = db_save_function

    def register_db_save_function(self, db_save_function: callable):
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

class DummyBus:
    def __init__(self):
        self.bus_lock = Lock()

    async def query(self, command: str):
        async with self.bus_lock:
            await anyio.sleep(0.1)
            return random.uniform(0, 100)
class DummySensor:
    def __init__(self, parameter: str, bus: DummyBus, db_save_function: callable | None = None):
        self.parameter = parameter
        self.bus = bus
        self.db_save_function = db_save_function
        self.confidence = Confidence(interval=0.5, level=0.95)
        self.units = "%" if parameter == "humidity" else "°C" if parameter == "temperature" else "lux"
        self.time_between_reads = random.uniform(0.5, 1.5)

    def register_db_save_function(self, db_save_function: callable):
        self.db_save_function = db_save_function

    async def read(self):
        value = await self.bus.query(f"Read {self.parameter}")
        await self.db_save_function(
            Datapoint(
                parameter=self.parameter,
                value=value,
                confidence=self.confidence,
                units=self.units
            )
        )
        return value
    
    async def reading_loop(self):
        while True:
            await self.read()
            await anyio.sleep(self.time_between_reads)

class DummyUnit:
    def __init__(self, name: str, db_client: DatabaseClient):
        self.name = name
        self.db_client = db_client
        self.db_lock = Lock()
        self.sensors = []
    
    async def db_save_function(self, datapoint: Datapoint):
        async with self.db_lock:
            self.db_client.write_measurement(self.name, datapoint)

    def register_sensor(self, parameter: str, bus: DummyBus):
        self.sensors.append(DummySensor(parameter, bus, self.db_save_function))

    async def start_sensing(self):
        async with create_task_group() as tg:
            for sensor in self.sensors:
                tg.start_soon(sensor.reading_loop)