import json, os
from typing import Any

import anyio

from .com_bus import Bus
from .database import DatabaseClient
from .pumps.ad20p_1230e import CS_IO404_Based_AD20P_1230E
from .unit import Unit
from . import pump_schedules, sensors

class Plant(Unit):
    def __init__(
            self,
            config: dict,
            db_client: DatabaseClient,
            busses: dict[str, Bus],
            schedules_directory: str
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
                    parameter=sensor_name,
                    busses=busses,
                    db_save_function=self.db_save_function,
                    sensor_kwargs=kwargs
                )
            )

        pump_config = config["actuators"]["water_pump"]

        self.pump = CS_IO404_Based_AD20P_1230E(
            bus=busses[CS_IO404_Based_AD20P_1230E.bus_type()],
            db_save_function=self.db_save_function,
            calibration_parameters=pump_config["calibration"],
            relay_address=pump_config["relay_address"],
            coil_number=pump_config["coil_number"]
        )

        self.schedule_location = os.path.join(schedules_directory, self.name + ".json")
        self.schedule = None
        self.pump_schedule_coroutine_cancel_scope = None
    
    def update_schedule(self, schedule: dict[str, Any]):
        if self.pump_schedule_coroutine_cancel_scope != None:
            self.pump_schedule_coroutine_cancel_scope.cancel()
        pump_schedules.validate_schedule(schedule)
        with open(self.schedule_location, 'w', encoding="utf-8") as schedule_file:
            schedule_file.write(json.dumps(schedule, indent=4))

    async def start_watering(self):
        while True:
            with anyio.CancelScope() as scope:
                self.pump_schedule_coroutine_cancel_scope = scope
                self.schedule = pump_schedules.parse_schedule(self.schedule_location)
                await self.schedule.run_schedule(self.pump.pumping_callback)

    def has_actuation(self) -> bool:
        return True

    @staticmethod
    def parse_config(path: str) -> dict:
        name = os.path.basename(os.path.splitext(path)[0])
        with open(path, "rb") as f:
            return {"name": name, **json.loads(f.read())}