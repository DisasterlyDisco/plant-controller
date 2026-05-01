from typing import Any

from .database import DatabaseClient
from .sensors import init_sensor
from .unit import Unit

class Greenhouse(Unit):
    def __init__(self, db_client: DatabaseClient, busses: dict[str, Any]):
        super().__init__(name="greenhouse", db_client=db_client)
        self.register_sensor(init_sensor(
            module_name="as7341",
            class_name="GreenhouseAS7341",
            parameter="_", # Defined by sensor 
            busses=busses,
            db_save_function=self.db_save_function
        ))
        self.register_sensor(init_sensor(
            module_name="sht45",
            class_name="GreenhouseSHT45",
            parameter="_", # Defined by sensor
            busses=busses,
            db_save_function=self.db_save_function
        ))
