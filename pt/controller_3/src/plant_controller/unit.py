import anyio
import argparse

from .database import DatabaseClient
from .datapoint import Datapoint
from .setup_actions import HasSetupFunctionsMixin

class Unit(HasSetupFunctionsMixin):
    def __init__(self, name: str, db_client: DatabaseClient):
        self.name = name
        self.db_client = db_client
        self.db_lock = anyio.Lock()
        self.sensors = []
    
    def register_sensor(self, new_sensor):
        for sensor in self.sensors:
            for parameter in list(sensor.get_capabilities()):
                if parameter in new_sensor.get_capabilities():
                    raise ValueError(f"Sensor with parameter '{parameter}' already exists in unit '{self.name}'. Each sensor must have unique parameters. If two sensors have overlapping parameters, consider combining them into a single sensor, or specifying the differences in their parameters.")
        self.sensors.append(new_sensor)

    async def start_sensing(self):
        async with anyio.create_task_group() as tg:
            for sensor in self.sensors:
                tg.start_soon(sensor.reading_loop)
    
    async def db_save_function(self, data: Datapoint | list[Datapoint]):
        async with self.db_lock:
            self.db_client.write_measurements(self.name, data)
    
    def get_sensing_capabilites(self):
        capabilities = {}
        for sensor in self.sensors:
            capabilities = {**capabilities, **sensor.get_capabilities()}
        return capabilities
    
    def has_actuation(self) -> bool:
        return False