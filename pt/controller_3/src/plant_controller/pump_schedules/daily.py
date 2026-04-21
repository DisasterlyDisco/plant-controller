from collections.abs import Callable
from typing import Any
import datetime
import time

import anyio

from .pump_schedules import PumpSchedule

class Schedule(PumpSchedule):
    def __init__(self, schedule: Any | None):
        self.schedule_list = sorted(list(
                map(
                    lambda event: (datetime.time.fromisoformat(event["time"]), event["dose"]),
                    schedule
                )
            ),
            lambda event: event[0]
        )

    async def run_schedule(self, pump_function: Callable[[int], None]):
        while(1):
            wait_until = None
            today = datetime.date.today()
            current_time = datetime.datetime.now()
            for event in self.schedule_list:
                datetime_event = datetime.datetime.combine(today, event[0])
                if current_time < datetime_event:
                    wait_until = datetime_event.timestamp()
                    dose = event[1]
        
            # Current time is later than last time for the day:
            if wait_until == None:
                tomorrow = today + datetime.timedelta(hours=24)
                tomorrows_first_event = self.schedule_list[0]
                tomorrows_first_event_datetime = datetime.datetime.combine(
                    tomorrow, tomorrows_first_event[0]
                )
                wait_until = tomorrows_first_event_datetime.timestamp()
                dose = tomorrows_first_event[1]
        
            await anyio.sleep_until(wait_until)

            pump_function(dose)
