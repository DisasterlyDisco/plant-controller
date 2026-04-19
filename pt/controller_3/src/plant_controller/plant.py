import json, os

from .com_bus import Bus
from .database import DatabaseClient
from .datapoint import Confidence, Datapoint
from . import plant_sensor_drivers
from .sensor import Sensor
from .unit import Unit

class Plant(Unit):
    def __init__(
            self,
            config: dict,
            db_client: DatabaseClient,
            busses: dict[str, Bus]
        ):
        if "name" not in config:
            raise ValueError("Unit config must include a 'name' field.")
        super().__init__(name=config["name"], db_client=db_client)
        self.sensors = []
        for sensor_name in config["sensors"]:
            sensor_config = config["sensors"][sensor_name]
            if "class" not in sensor_config:
                raise ValueError(f"Sensor config for '{sensor_name}' must include a 'class' field.")
            if "kwargs" in sensor_config:
                kwargs = sensor_config["kwargs"]
            else:
                kwargs = {}
            sensor_class = getattr(plant_sensor_drivers, sensor_config["class"])
            self.register_sensor(sensor_class(busses=busses, db_save_function=self.db_save_function, **kwargs))
            
    @staticmethod
    def parse_config(path: str) -> dict:
        name = os.path.basename(path)
        with open(path, "rb") as f:
            return {"name": name, **json.loads(f.read())}