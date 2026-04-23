from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
import importlib, json

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

def parse_schedule(schedule_location: str) -> PumpSchedule:
    with open(schedule_location, "rb") as schedule_file:
        schedule_dict = json.loads(schedule_file.read())
    schedule_module = importlib.import_module(__name__ + "." + schedule_dict["type"])
    return getattr(schedule_module, "Schedule")(schedule_dict.get("schedule"))

def validate_schedule(schedule_config: dict[str, Any]):
    """
    Validates the contents of a schedule config.

    Raises a ValueError incase the schedule is invalid.
    
    :param schedule_config: dict describing a Schedule.
    :type schedule_config: dict[str, Any]
    :raises: ValueError
    """
    pass