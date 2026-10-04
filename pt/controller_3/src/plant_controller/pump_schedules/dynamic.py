import logging
_logger = logging.getLogger(__name__)

from collections.abc import Coroutine
from typing import Any

import anyio

from . import PumpSchedule

LINKED_PARAMETER = "linked_sensed_parameter"
HIGH_POINT = "high_point"
LOW_POINT = "low_point"
CLIMBING_DOSE = "watering_dose_increment_when_climbing_in_milliliters"
CLIMBING_REST_TIME = "time_in_seconds_between_watering_when_climbing"
FALLING_TBS = "time_in_seconds_between_sensing_when_falling"

class Schedule(PumpSchedule):

    def __init__(self, details: Any | None):
        self.linked_parameter = details[LINKED_PARAMETER]
        self.high_point = details[HIGH_POINT]
        self.low_point = details[LOW_POINT]
        self.climbing_dose = details[CLIMBING_DOSE]
        self.climbing_rest_time = details[CLIMBING_REST_TIME]
        self.falling_tbs = details[FALLING_TBS]
        self.climbing = False

    def register_plant(self, plant):
        self._get_current_moisture_level = lambda: plant.db_client.read_measurements(
            physical_unit=plant.name,
            parameter=self.linked_parameter,
            limit=1
        )
    
    def get_details(self) -> dict:
        return {
            LINKED_PARAMETER: self.linked_parameter,
            HIGH_POINT: self.high_point,
            LOW_POINT: self.low_point,
            CLIMBING_DOSE: self.climbing_dose,
            CLIMBING_REST_TIME: self.climbing_rest_time,
            FALLING_TBS: self.falling_tbs
        }
    
    async def run_schedule(self, pump_function: Coroutine[Any, int]):
        while True:
            if self.climbing:
                if self._get_current_moisture_level() > self.high_point:
                    self.climbing = False
                else:
                    await pump_function(self.climbing_dose)
                    await anyio.sleep(self.climbing_rest_time)
            else:
                if self._get_current_moisture_level() < self.low_point:
                    self.climbing = True
                else:
                    await anyio.sleep(self.falling_tbs)

    @staticmethod
    def validate_schedule_details(schedule_details: Any):
        if not isinstance(schedule_details, dict):
            raise ValueError("A schedule of type 'dynamic' needs a dictionary with configuration parameters in the 'details' value.")
        
        if LINKED_PARAMETER not in schedule_details:
            raise ValueError("")
        
        if HIGH_POINT not in schedule_details:
            raise ValueError("")
        
        if LOW_POINT not in schedule_details:
            raise ValueError("")
        
        if CLIMBING_DOSE not in schedule_details:
            raise ValueError("")
        
        if CLIMBING_REST_TIME not in schedule_details:
            raise ValueError("")
        
        if FALLING_TBS not in schedule_details:
            raise ValueError("")

