import anyio

from .database import DatabaseClient
from .datapoint import Datapoint

class Unit():
    def __init__(self, name: str, db_client: DatabaseClient):
        self.name = name
        self.db_client = db_client
        self.db_lock = anyio.Lock()
        self.sensors = []
    
    async def start_sensing(self):
        async with anyio.create_task_group() as tg:
            for sensor in self.sensors:
                tg.start_soon(sensor.reading_loop)
    
    async def db_save_function(self, datapoint: Datapoint):
        async with self.db_lock:
            self.db_client.write_measurement(self.name, datapoint)