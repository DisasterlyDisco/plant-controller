import logging
logger = logging.getLogger(__name__)

from collections.abc import Coroutine
from typing import Any
import datetime

import anyio

from . import PumpSchedule

class Schedule(PumpSchedule):
    def __init__(self, schedule: Any | None):
        self.schedule_list = sorted(list(
                map(
                    lambda event: (datetime.time.fromisoformat(event["time"]), event["dose"]),
                    schedule
                )
            ),
            key=lambda event: event[0]
        )
    
    def get_schedule(self) -> str  | dict:
        return {
            "type": "daily",
            "description": "Daily watering schedule. The plant is watered each day at the given times.",
            "schedule": self.schedule_list
        }

    async def run_schedule(self, pump_function: Coroutine[Any, int]):
        if len(self.schedule_list) < 1:
            logger.warning("No watering events in schedule, skipping watering.")
            await anyio.sleep_forever()

        while True:
            sleep_time = None
            today = datetime.date.today()
            current_time = datetime.datetime.now()
            for event in self.schedule_list:
                datetime_event = datetime.datetime.combine(today, event[0])
                if current_time < datetime_event:
                    sleep_time_delta = (datetime_event - current_time)
                    sleep_time = sleep_time_delta.total_seconds()
                    dose = event[1]
                    break
        
            # Current time is later than last time for the day:
            if sleep_time == None:
                tomorrow = today + datetime.timedelta(hours=24)
                tomorrows_first_event = self.schedule_list[0]
                tomorrows_first_event_datetime = datetime.datetime.combine(
                    tomorrow, tomorrows_first_event[0]
                )
                sleep_time_delta = tomorrows_first_event_datetime - current_time
                sleep_time = sleep_time_delta.total_seconds()
                dose = tomorrows_first_event[1]
            logger.info(f"Current time is {current_time.isoformat()}. Next watering event is at {event[0].isoformat()} with a dose of {dose} ml. Scheduled to sleep for {sleep_time_delta}.")
        
            await anyio.sleep(sleep_time)

            await pump_function(dose)

    def validate_schedule_conf(schedule_conf: Any):
        if not isinstance(schedule_conf, list):
            raise ValueError("A schedule of type 'daily' needs a list of dictionaries containing watering events in the 'schedule' value.")
        
        for entry in schedule_conf:
            if not isinstance(entry, dict):
                raise ValueError("Each entry in the daily schedules 'schedule' list must be a dictionary.")
            
            if "time" not in entry:
                raise ValueError("Each entry in the daily schedules 'schedule' list must contain a 'time' entry.")
            
            try:
                datetime.time.fromisoformat(entry["time"])
            except Exception as e:
                raise ValueError("Each 'time' in each entry in the daily schedules 'schedule' list must be a proper time following the ISO 8601 standard.")
            
            if "dose" not in entry:
                raise ValueError("Each entry in the daily schedules 'schedule' list must contain a 'dose' entry.")
            
            if not isinstance(entry["dose"], int):
                raise ValueError("Each 'dose' in each entry in the daily schedules 'schedule' list must be an integer.")
