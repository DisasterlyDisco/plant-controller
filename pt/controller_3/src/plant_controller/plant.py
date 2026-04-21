import importlib, json, os

from .com_bus import Bus
from .database import DatabaseClient
from .unit import Unit
from . import sensors

#_PLANT_SENSOR_DRIVERS_PACKAGE = "plant_controller.plant_sensor_drivers"

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
            if "module" not in sensor_config:
                raise ValueError(f"Sensor config for '{sensor_name}' must include a 'module' field.")
            if "class" not in sensor_config:
                raise ValueError(f"Sensor config for '{sensor_name}' must include a 'class' field.")
            if "kwargs" in sensor_config:
                kwargs = sensor_config["kwargs"]
            else:
                kwargs = {}
            self.register_sensor(
                sensors.init_sensor(
                    module_name=sensor_config['module'],
                    class_name=sensor_config["class"],
                    name=sensor_name,
                    busses=busses,
                    db_save_function=self.db_save_function,
                    sensor_kwargs=kwargs
                )
            )
            #module = importlib.import_module(f"{_PLANT_SENSOR_DRIVERS_PACKAGE}.{sensor_config['module']}")
            #sensor_class = getattr(module, sensor_config["class"])
            #self.register_sensor(sensor_class(busses=busses, db_save_function=self.db_save_function, **kwargs))
            
    @staticmethod
    def parse_config(path: str) -> dict:
        name = os.path.basename(os.path.splitext(path)[0])
        with open(path, "rb") as f:
            return {"name": name, **json.loads(f.read())}