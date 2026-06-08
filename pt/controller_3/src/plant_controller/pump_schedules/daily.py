"""Daily pump schedule implementation.

Waters the plant at fixed times each day with specified dosages. The
schedule repeats every 24 hours.

Schedule JSON format::

    {
        "type": "daily",
        "schedule": [
            {"time": "08:00", "dose": 50},
            {"time": "18:00", "dose": 75}
        ]
    }

Each entry's "time" must be an ISO 8601 time string (HH:MM or HH:MM:SS).
Each "dose" is an integer number of milliliters.
"""

import logging
_logger = logging.getLogger(__name__)

from collections.abc import Coroutine
from typing import Any
import datetime

import anyio

from . import PumpSchedule


class Schedule(PumpSchedule):
    """Daily repeating watering schedule.

    Waters at fixed times each day. Events are sorted chronologically.
    If the current time is past all events for today, the schedule sleeps
    until the first event tomorrow.

    Attributes:
        schedule_list: Sorted list of (time, dose) tuples.
    """

    def __init__(self, schedule: Any | None):
        """Parse the schedule list into sorted (time, dose) tuples.

        Args:
            schedule: List of dicts with 'time' (ISO time str) and
                'dose' (int, ml) keys.
        """
        self.schedule_list = sorted(list(
                map(
                    lambda event: {
                        "time": datetime.time.fromisoformat(event["time"]),
                        "dose": event["dose"]
                    },
                    schedule
                )
            ),
            key=lambda event: event["time"]
        )
    
    def get_schedule(self) -> str | dict:
        """Return a dict describing the daily schedule and its events."""
        return {
            "type": "daily",
            "description": "Daily watering schedule. The plant is watered each day at the given times.",
            "schedule": self.schedule_list
        }

    async def run_schedule(self, pump_function: Coroutine[Any, int]):
        """Sleep until the next scheduled time, then pump. Repeats forever.

        Args:
            pump_function: Async callback to activate the pump with a dosage.
        """
        if len(self.schedule_list) < 1:
            _logger.warning("No watering events in schedule, skipping watering.")
            await anyio.sleep_forever()

        while True:
            sleep_time = None
            today = datetime.date.today()
            current_time = datetime.datetime.now()
            for event in self.schedule_list:
                datetime_event = datetime.datetime.combine(today, event["time"])
                if current_time < datetime_event:
                    sleep_time_delta = datetime_event - current_time
                    sleep_time = sleep_time_delta.total_seconds()
                    dose = event["dose"]
                    break
        
            # Current time is later than last time for the day:
            if sleep_time == None:
                tomorrow = today + datetime.timedelta(days=1)
                tomorrows_first_event = self.schedule_list[0]
                datetime_event = datetime.datetime.combine(
                    tomorrow, tomorrows_first_event["time"]
                )
                sleep_time_delta = datetime_event - current_time
                sleep_time = sleep_time_delta.total_seconds()
                dose = tomorrows_first_event["dose"]
                
            _logger.info(f"Current time is {current_time.isoformat()}. Next watering event is at {datetime_event.isoformat()} with a dose of {dose} ml. Scheduled to sleep for {sleep_time_delta}.")
        
            await anyio.sleep(sleep_time)

            await pump_function(dose)

    @staticmethod
    def validate_schedule_conf(schedule_conf: Any):
        """Validate that schedule_conf is a list of {time, dose} dicts.

        Args:
            schedule_conf: The "schedule" field from the config JSON.

        Raises:
            ValueError: If format requirements are not met.
        """
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
