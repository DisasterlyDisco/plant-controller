"""Pump schedule modules for automated watering.

This package defines the abstract base class for pump schedules and provides
the dynamic loading mechanism. Schedules control *when* and *how much* water
is delivered to a plant.

Writing a custom schedule module:
    1. Create a new ``.py`` file in this package (e.g. ``my_schedule.py``).
    2. Define a class called **exactly** ``Schedule`` that inherits from
       ``PumpSchedule``.
    3. Implement the three abstract methods: ``__init__``, ``get_schedule``,
       and ``run_schedule``.
    4. Optionally implement ``validate_schedule`` as a ``@staticmethod``
       to validate config data before instantiation.
    5. Create a schedule JSON file in ``~/.plant_controller/pump_schedules/``
       named ``<plant_name>.json``::

           {
               "type": "my_schedule",
               "schedule": { ... schedule-specific data ... }
           }

       The ``"type"`` value must match the module filename (without .py).
       The ``"schedule"`` value is passed to ``Schedule.__init__``.

Example minimal schedule::

    import anyio
    from plant_controller.pump_schedules import PumpSchedule

    class Schedule(PumpSchedule):
        def __init__(self, schedule):
            self.dose = schedule["dose_ml"]
            self.interval = schedule["interval_seconds"]

        def get_schedule(self):
            return f"Pump {self.dose}ml every {self.interval}s"

        async def run_schedule(self, pump_function):
            while True:
                await anyio.sleep(self.interval)
                await pump_function(self.dose)

        @staticmethod
        def validate_schedule(schedule_conf):
            if "dose_ml" not in schedule_conf:
                raise ValueError("Must include 'dose_ml'")
            if "interval_seconds" not in schedule_conf:
                raise ValueError("Must include 'interval_seconds'")
"""

import logging
_logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
import importlib, json

import anyio
from pydantic import BaseModel

class WateringScheduleBaseRepresentation(BaseModel):
    type: str
    description: str | None = None
    details: Any

class PumpSchedule(ABC):
    """Abstract base class for all pump schedule implementations.

    A pump schedule determines when watering events occur and how much water
    is delivered. The schedule has full control over timing, enabling both
    simple time-based schedules and dynamic sensor-driven strategies.

    Subclasses must be named ``Schedule`` in their module so that the dynamic
    loader can find them.
    """

    @abstractmethod
    def __init__(self, schedule: Any | None):
        """Initialize the schedule from configuration data.

        The ``schedule`` parameter receives whatever was in the "schedule"
        field of the JSON config file. Its structure is entirely up to the
        implementer.

        Args:
            schedule: Schedule-specific configuration data (type defined by
                the implementation). May be None if the schedule requires no
                configuration.
        """
        pass

    @abstractmethod
    def get_schedule(self) -> str | dict:
        """Return a human-readable representation of this schedule.

        This is served via the HTTP API so that users can inspect the
        current watering plan without reading config files.

        Returns:
            A string description or dict (serialized as JSON) explaining
            when watering will occur and at what dosages.
        """
        pass

    @abstractmethod
    async def run_schedule(self, pump_function: Callable[[int], None]):
        """Execute the schedule, calling pump_function at appropriate times.

        This coroutine runs indefinitely. It should await ``anyio.sleep()``
        until the next watering event, then call
        ``await pump_function(dosage_ml)`` to trigger the pump.

        The method must not return under normal operation. If the schedule
        is cancelled externally (via CancelScope), it will be restarted
        with a freshly parsed config.

        Args:
            pump_function: Async callback that activates the pump.
                Call with an integer dosage in milliliters.
        """
        pass

    @staticmethod
    def validate_schedule(schedule_conf: Any):
        """Validate schedule-specific configuration data.

        Called during schedule loading to catch config errors early.
        Should raise ``ValueError`` with a descriptive message if the
        configuration is invalid.

        If validation is not needed, this method can be left as a no-op.

        Args:
            schedule_conf: The "schedule" field from the JSON config file.

        Raises:
            ValueError: If the configuration is invalid.
        """
        pass

class NonSchedule(PumpSchedule):
    """A no-op schedule that never triggers watering.

    Used as a fallback when no valid schedule config exists or when
    schedule parsing fails.
    """

    def __init__(self, schedule: Any | None = None):
        pass

    def get_schedule(self) -> str:
        return "No schedule, the plant will not be watered automatically."

    async def run_schedule(self, pump_function: Callable[[int], None]):
        _logger.warning("Plant running empty schedule, no watering will happen.")
        await anyio.sleep_forever()

def parse_schedule(schedule_location: str) -> PumpSchedule:
    """Load and instantiate a PumpSchedule from a JSON config file.

    If the file cannot be loaded or is invalid, returns a NonSchedule
    instance and logs the error.

    Args:
        schedule_location: Filesystem path to the schedule JSON file.

    Returns:
        An initialized PumpSchedule instance (or NonSchedule on failure).
    """
    try:
        with open(schedule_location, "rb") as schedule_file:
            schedule_dict = json.loads(schedule_file.read())
        validate_schedule_config(schedule_dict)
        schedule_module = importlib.import_module(__name__ + "." + schedule_dict["type"])
        return getattr(schedule_module, "Schedule")(schedule_dict.get("schedule"))
    except ValueError as e:
        _logger.error(f"Schedule config at {schedule_location} is invalid: {e}")
        return NonSchedule()
    except Exception as e:
        _logger.error(f"Error loading schedule config at {schedule_location}: {e}")
        return NonSchedule()
        

def validate_schedule_config(schedule_config: dict[str, Any]):
    """Validate the top-level structure of a schedule config dict.

    Checks that the required 'type' and 'schedule' keys exist, that the
    referenced module can be imported and contains a 'Schedule' class,
    and delegates to that class's validate_schedule for content
    validation.

    Args:
        schedule_config: Parsed JSON dict with 'type' and 'schedule' keys.

    Raises:
        ValueError: If the config structure is invalid or the module/class
            cannot be loaded.
    """
    if "type" not in schedule_config:
        raise ValueError("Schedule must have a 'type' field, indicating type of the schedule and the underlying python module that defines it.")
    
    if "schedule" not in schedule_config:
        raise ValueError("Schedule must contain a value called 'schedule' containing type specefic details on the schedule, for example times and dosages.")
    
    if not isinstance(schedule_config["type"], str):
        raise ValueError("'type' field must be a string, indicating the type of the schedule and the underlying python module that defines it.")
    
    try:
        module_name = __name__ + "." + schedule_config["type"]
        schedule_module = importlib.import_module(module_name)
    except Exception as e:
        raise ValueError(f"Could not load the module {module_name}: {e}")
    
    try:
        schedule_class = getattr(schedule_module, "Schedule")
    except Exception as e:
        raise ValueError(f"Could not find the 'Schedule' class inside the schedules types module {module_name}")

    schedule_class.validate_schedule(schedule_config["schedule"])