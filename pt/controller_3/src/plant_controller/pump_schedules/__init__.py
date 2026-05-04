import logging
logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
import importlib, json

import anyio

class PumpSchedule(ABC):
    @abstractmethod
    def __init__(self, schedule: Any | None):
        """
        Creates the Schedule objet.

        Including the 'schedule' parameter is mandatory - using it is not.
        The structure and type of 'schedule' is left up to the implementer.
        
        :param schedule: Any 
        :type schedule: Any | None
        """
        pass
    
    @abstractmethod
    def get_schedule(self) -> str | dict:
        """
        Returns a representation of the schedule.

        This should return an overview of the scheduled watering events, or
        at least explain how the schedule works, so that someone not familiar
        with the schedules implementation can intuit when watering will happen
        and how much water will be dosed.
        
        :return: The overwiew. If in a dict, expect it to be expressed as a json object
        :rtype: str | dict
        """
        pass

    @abstractmethod
    async def run_schedule(self, pump_function: Callable[[int], None]):
        """
        Calls the given pump function according to the schedule defined in the
        implementation of this class.

        The dosage as specified by the schedule should be passed to the
        pump function.

        The intent is to put the responsibility for when the pumping should be
        done entirely on the schedule, allowing for both basic time based
        schedules and more dynamic, sensing based schedules
        
        :param pump_function: Callback function that runs the pump that should
                              be activated at the scheduled time, pumping the
                              desired dosage.
        :type pump_function: Callable[[int], None])
        """
        pass

    def validate_schedule_conf(schedule_conf: Any):
        """
        Goes through the passed schedule_conf and ensures that it is properly
        formatted, raising ValueErrors if not.

        If validation is unwanted or irrelevant, then this method can be left
        unimplemented.
        
        :param schedule_conf: Description
        :type schedule_conf: Any
        """
        pass

class NonSchedule(PumpSchedule):
    def __init__(self, schedule: Any | None = None):
        pass
    
    def get_schedule(self) -> str:
        return "No schedule, the plant will not be watered automatically."
    
    async def run_schedule(self, pump_function: Callable[[int], None]):
        logger.warning("Plant running empty schedule, no watering will happen.")
        await anyio.sleep_forever()

def parse_schedule(schedule_location: str) -> PumpSchedule:
    try:
        with open(schedule_location, "rb") as schedule_file:
            schedule_dict = json.loads(schedule_file.read())
        validate_schedule(schedule_dict)
        schedule_module = importlib.import_module(__name__ + "." + schedule_dict["type"])
        return getattr(schedule_module, "Schedule")(schedule_dict.get("schedule"))
    except ValueError as e:
        logger.error(f"Schedule config at {schedule_location} is invalid: {e}")
        return NonSchedule()
    except Exception as e:
        logger.error(f"Error loading schedule config at {schedule_location}: {e}")
        return NonSchedule()
        

def validate_schedule(schedule_config: dict[str, Any]):
    """
    Validates the contents of a schedule config.

    Raises a ValueError incase the schedule is invalid.
    
    :param schedule_config: dict describing a Schedule.
    :type schedule_config: dict[str, Any]
    :raises: ValueError
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

    schedule_class.validate_schedule_conf(schedule_config["schedule"])