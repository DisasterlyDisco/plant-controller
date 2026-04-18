import sys, random

import anyio

from . import datapoint, database, web_api
from .sensor import DummyBus, DummyUnit

async def main():

    print("Setting up DB")
    db = database.Database(
        token=sys.argv[1]
    )
    print("DB Done!")
    
    print("Spinning up web API")
    api = web_api.WebAPI(
        host="0.0.0.0",
        port=8099,
        db_client=db.spawn_client()
    )

    print("Setting up greenhouse and sensors")
    bus = DummyBus()
    unit = DummyUnit("greenhouse_1", db.spawn_client())
    unit.register_sensor("temperature", bus)
    unit.register_sensor("humidity", bus)
    unit.register_sensor("light", bus)

    async with anyio.create_task_group() as tg:
        tg.start_soon(api.start)
        tg.start_soon(unit.start_sensing)
    