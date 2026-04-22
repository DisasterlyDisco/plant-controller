import os, tomllib

import anyio

from . import com_bus, database, greenhouse, plant, web_api

_IMPL_DIR = "../impl"
_CONFIG_PATH = os.path.join(_IMPL_DIR, "config.toml")
_PLANTS_DIR = os.path.join(_IMPL_DIR, "plants")

async def main():
    print("Loading config")
    with open(_CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)

    print("Setting up DB")
    db = database.Database(
        name=config["database"]["name"],
        host=config["database"]["host"],
        token=config["database"]["token"]
    )
    print("DB Done!")

    print("Setting up com busses")
    busses = {
        "i2c": com_bus.DummmyI2CBus(),
        "MODBUS": com_bus.DummyMODBUS()
    }

    print("Setting up units")
    units = []
    units.append(
        greenhouse.Greenhouse(
            db_client=db.spawn_client(),
            i2c_bus=busses["i2c"]
        )
    )
    plant_configs = [
        plant.Plant.parse_config(os.path.join(_PLANTS_DIR, f))
        for f
        in os.listdir(_PLANTS_DIR)
        if f.endswith(".json")
    ]
    for config in plant_configs:
        units.append(
            plant.Plant(
                config=config,
                db_client=db.spawn_client(),
                busses=busses
            )
        )
    print("Units done!")

    units_overview = {unit.name: unit.get_sensing_capabilites() for unit in units}
    print("Units overview:")
    for unit_name, capabilities in units_overview.items():
        print(f"  {unit_name}:")
        for param, info in capabilities.items():
            print(f"    {param}: {info}")

    print("Spinning up web API")
    api = web_api.WebAPI(
        host="0.0.0.0",
        port=8099,
        db_client=db.spawn_client(),
        units_overview=units_overview
    )

    async with anyio.create_task_group() as tg:
        tg.start_soon(api.start)
        for unit in units:
            tg.start_soon(unit.start_sensing)
    