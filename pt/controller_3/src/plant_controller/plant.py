"""Plant unit module.

A Plant is a Unit that has both sensors and a water pump attached.
It manages pump schedules and provides watering actuation in addition
to the base sensing functionality.
"""

import logging
_logger = logging.getLogger(__name__)

import datetime, json, os
from typing import Any, Callable

import anyio

from .com_bus import Bus
from .database import DatabaseClient
from .pumps.ad20p_1230e import CS_IO404_Based_AD20P_1230E
from .unit import Unit
from . import pump_schedules, sensors


class Plant(Unit):
    """A plant unit with sensors and a calibrated water pump.

    Plants are configured via JSON files in ``~/.plant_controller/plants/``.
    Each plant has one pump and one or more sensors, all specified in the
    config. Watering is controlled by a pump schedule loaded from
    ``~/.plant_controller/pump_schedules/<plant_name>.json``.

    Attributes:
        config: The parsed plant configuration dict.
        config_path: Filesystem path to the plant's JSON config file.
        pump: The pump instance attached to this plant.
        schedule: The active PumpSchedule instance.
        schedule_location: Path to the pump schedule JSON file.
    """
    def __init__(
            self,
            config: dict,
            db_client: DatabaseClient,
            busses: dict[str, Bus],
            schedules_directory: str,
            config_path: str | None = None
        ):
        """Initialize the plant from a configuration dict.

        Args:
            config: Parsed plant config (must include 'name', 'sensors',
                and 'actuators.water_pump' sections).
            db_client: Database client for persisting data.
            busses: Dict of available bus instances.
            schedules_directory: Directory containing pump schedule JSONs.
            config_path: Path to the config file (for saving changes back).

        Raises:
            ValueError: If required config fields are missing.
        """
        self.config = config
        self.config_path = config_path

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
                    config_save_function=self.sensor_specific_config_save_function(sensor_name),
                    sensor_kwargs=kwargs
                )
            )

        pump_config = config["actuators"]["water_pump"]

        if "calibration_date" not in pump_config["calibration"]:
            _logger.warning(f"The pump for plant '{self.name}' has not yet been calibrated.")

        self.pump = CS_IO404_Based_AD20P_1230E(
            bus=busses[CS_IO404_Based_AD20P_1230E.bus_type()],
            db_save_function=self.db_save_function,
            calibration_save_function=self.save_pump_calibration,
            calibration_parameters=pump_config["calibration"],
            relay_address=pump_config["relay_address"],
            coil_number=pump_config["coil_number"]
        )

        self.schedule_location = os.path.join(schedules_directory, self.name + ".json")
        self.schedule = pump_schedules.NonSchedule()
        self.pump_schedule_coroutine_cancel_scope = None
    
    def update_schedule(self, schedule: pump_schedules.BaseRepresentation):
        """Validate and apply a new pump schedule, persisting it to disk.

        Cancels any currently running schedule coroutine so that it
        restarts with the new configuration.

        Args:
            schedule: A schedule config dict with 'type' and 'schedule' keys.

        Raises:
            ValueError: If the schedule config is invalid.
        """
        if self.pump_schedule_coroutine_cancel_scope is not None:
            self.pump_schedule_coroutine_cancel_scope.cancel()
        with open(self.schedule_location, 'w', encoding="utf-8") as schedule_file:
            schedule_file.write(schedule.model_dump_json(indent=4))
    
    def save_configuration(self):
        """Persist the current config dict back to the JSON file.

        Raises:
            ValueError: If no config_path was provided at init time.
        """
        if self.config_path == None:
            raise ValueError("No configuration path provided for this plant, cannot save configuration.")
        with open(self.config_path, 'w', encoding="utf-8") as config_file:
            config_file.write(json.dumps(self.config, indent=4))

    def sensor_specific_config_save_function(self, sensor_name) -> Callable:
        """Create a config save callback scoped to a specific sensor.

        Returns a callable that, when called with keyword arguments, merges
        them into the sensor's ``kwargs`` section in the plant config and
        persists the result to disk.

        Args:
            sensor_name: Name of the sensor in the config's ``sensors`` dict.

        Returns:
            A callable accepting ``**kwargs`` that saves them to the config.
        """
        def update_sensor_config(**kwargs):
            for key, value in kwargs.items():
                self.config["sensors"][sensor_name].setdefault("kwargs", {})[key] = value
            self.save_configuration()
        return update_sensor_config
    
    def save_pump_calibration(self, slope: float, offset: float):
        """Save new pump calibration parameters to the plant config.

        Args:
            slope: Linear calibration slope (seconds per ml).
            offset: Linear calibration offset (seconds).
        """
        self.config["actuators"]["water_pump"]["calibration"]["slope"] = slope
        self.config["actuators"]["water_pump"]["calibration"]["offset"] = offset
        self.config["actuators"]["water_pump"]["calibration"]["calibration_date"] = datetime.datetime.now().isoformat()
        self.save_configuration()

    async def start_watering(self):
        """Run the pump schedule in a loop, restarting on cancellation.

        When the schedule's cancel scope is cancelled (e.g. after an
        update_schedule call), the schedule is re-parsed from disk and
        restarted.
        """
        _logger.debug(f"Plant {self.name} started watering")
        while True:
            with anyio.CancelScope() as scope:
                self.pump_schedule_coroutine_cancel_scope = scope
                self.schedule = pump_schedules.parse_schedule(self.schedule_location)
                _logger.debug(f"Plant {self.name} watering started with schedule.")
                await self.schedule.run_schedule(self.pump.pumping_callback)
            _logger.debug(f"Plant {self.name} cancelled watering schedule.")

    def has_actuation(self) -> bool:
        """Return True — plants always have a pump attached."""
        return True

    @staticmethod
    def parse_config(path: str) -> dict:
        """Parse a plant JSON config file, injecting the filename as 'name'.

        If 'name' is already in the config file, the filename will be ignored.

        Args:
            path: Path to the plant's JSON configuration file.

        Returns:
            Config dict with 'name' key added from the filename.
        """
        name = os.path.basename(os.path.splitext(path)[0])
        with open(path, "rb") as f:
            return {"name": name, **json.loads(f.read())}

    def setup_functions(self) -> dict[str, dict[str, Any]]:
        """Collect setup functions from the pump and all sensors.

        Returns:
            Dict mapping action names (e.g. 'pump.calibrate') to dicts
            with 'description' and 'function' keys.
        """
        action_dict = {}

        if hasattr(self.pump, "setup_functions"):
            for func_name, func in self.pump.setup_functions().items():
                action_dict[f"pump.{func_name}"] = func

        for sensor in self.sensors:
            if hasattr(sensor, "setup_functions"):
                for func_name, func in sensor.setup_functions().items():
                    action_dict[f"sensor.{sensor.parameter}.{func_name}"] = func

        return action_dict