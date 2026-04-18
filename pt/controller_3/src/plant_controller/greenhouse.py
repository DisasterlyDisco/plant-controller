from .com_bus import Bus
from .database import DatabaseClient
from .unit import Unit

class Greenhouse(Unit):
    def __init__(self, db_client: DatabaseClient, i2c_bus: Bus):
        super().__init__(name="Greenhouse", db_client=db_client)
        self.i2c_bus = i2c_bus