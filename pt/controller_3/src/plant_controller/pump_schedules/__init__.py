"""Pump schedule modules for automated watering.

This package defines the abstract base class for pump schedules and provides
the dynamic loading mechanism. Schedules control *when* and *how much* water
is delivered to a plant.

Writing a custom schedule module:
    1. Create a new ``.py`` file in this package (e.g. ``my_schedule.py``).
    2. Define a class called **exactly** ``Schedule`` that inherits from
       ``PumpSchedule``.
    3. Implement the three abstract methods: ``__init__``, ``get_details``,
       and ``run_schedule``.
    4. Optionally implement ``validate_schedule_details`` as a
       ``@staticmethod`` to validate config data before instantiation,
       ``get_description`` to give a human description of what the
       schedule does, and the visiter method ``register_plant`` if necessary.
    5. Create a schedule JSON file in ``~/.plant_controller/pump_schedules/``
       named ``<plant_name>.json``::

           {
               "type": "my_schedule",
               "details": { ... schedule-specific data ... }
           }

       The ``"type"`` value must match the module filename (without .py).
       The ``"details"`` value is passed to ``Schedule.__init__``.

Example minimal schedule::

    import anyio
    from plant_controller.pump_schedules import PumpSchedule

    class Schedule(PumpSchedule):
        def __init__(self, details):
            self.dose = details["dose_ml"]
            self.interval = details["interval_seconds"]

        def get_description(self):
            return f"Pump {self.dose}ml every {self.interval}s"
        
        def get_details(self):
            return {
                "dose_ml": self.dose,
                "interval_seconds": self.interval
            }

        async def run_schedule(self, pump_function):
            while True:
                await anyio.sleep(self.interval)
                await pump_function(self.dose)

        @staticmethod
        def validate_schedule_details(schedule_details):
            if "dose_ml" not in schedule_details:
                raise ValueError("Must include 'dose_ml'")
            if "interval_seconds" not in schedule_details:
                raise ValueError("Must include 'interval_seconds'")
"""

import logging
_logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any
import importlib

import anyio
from pydantic import BaseModel

class BaseRepresentation(BaseModel):
    """Base Representation of a PumpSchedule.
    
    Any out of program representation of a PumpSchedule should contain these
    parameters if they are to be parsed as a PumpSchedule in program.

    Primarily used to define how a PumpSchedule is represented and stored
    as JSON.
    """
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
    def __init__(self, schedule_details: Any | None):
        """Initialize the schedule from configuration data.

        The ``schedule`` parameter receives whatever was in the "details"
        field of the JSON config file. Its structure is entirely up to the
        implementer.

        Args:
            schedule_Details: Schedule-specific configuration data (type
                defined by the implementation). May be None if the schedule
                requires no configuration.
        """
        pass

    def register_plant(self, plant):
        """Visiter method, to be called by Plants before running the schedule.
        
        Base implementation is a noop - may be extended by inheriting classes.
        """
        pass

    def json_representation(self) -> str:
        return BaseRepresentation(
            type=self.get_type(),
            description=self.get_description(),
            details=self.get_details()
        ).model_dump_json(indent=4)
    
    def get_type(self) -> str:
        return __name__
    
    def get_description(self) -> str | None:
        return None

    @abstractmethod
    def get_details(self) -> Any:
        pass

    @abstractmethod
    async def run_schedule(self, pump_function: Coroutine[Any, int]):
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
    def validate_schedule_details(schedule_details: Any):
        """Validate schedule-specific configuration data.

        Called during schedule loading to catch config errors early.
        Should raise ``ValueError`` with a descriptive message if the
        configuration is invalid.

        If validation is not needed, this method can be left as a no-op.

        Args:
            schedule_details: The "details" field from the JSON config file.

        Raises:
            ValueError: If the configuration is invalid.
        """
        pass

class NonSchedule(PumpSchedule):
    """A no-op schedule that never triggers watering.

    Used as a fallback when no valid schedule config exists or when
    schedule parsing fails.
    """

    def __init__(self, details: Any | None = None):
        pass

    def get_type(self) -> str:
        return "NO SCHEDULE!"
    
    def get_description(self) -> str | None:
        return "No valid schedule present for the plant; it will not be watered automatically. "
    
    def get_details(self) -> Any:
        return None

    async def run_schedule(self, pump_function: Coroutine[Any, int]):
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
            schedule_representation = BaseRepresentation.model_validate_json(schedule_file.read())
        return validate_schedule_representation(schedule_representation)
    except ValueError as e:
        _logger.error(f"Schedule config at {schedule_location} is invalid: {e}")
        return NonSchedule()
    except Exception as e:
        _logger.error(f"Error loading schedule config at {schedule_location}: {e}")
        return NonSchedule()

def validate_schedule_representation(schedule_representation) -> PumpSchedule:
    try:
        module_name = __name__ + "." + schedule_representation.type
        schedule_module = importlib.import_module(module_name)
    except Exception as e:
        raise ValueError(f"Could not load the module {module_name}: {e}")
    
    try:
        schedule_class = getattr(schedule_module, "Schedule")
    except Exception as e:
        raise ValueError(f"Could not find the 'Schedule' class inside the schedules types module {module_name}")
    
    schedule_class.validate_schedule_details(schedule_representation.details)

    return getattr(schedule_module, "Schedule")(schedule_representation.details)
