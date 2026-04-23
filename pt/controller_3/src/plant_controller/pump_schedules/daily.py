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

    async def run_schedule(self, pump_function: Coroutine[Any, int]):
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
            
            print(f"Scheduled to sleep for {sleep_time_delta}")
        
            await anyio.sleep(sleep_time)

            await pump_function(dose)
