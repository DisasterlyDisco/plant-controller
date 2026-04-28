import os
import tomllib

import anyio

from . import com_bus, database, greenhouse, plant, web_api

_IMPL_DIR = os.path.abspath("../impl")
_CONFIG_PATH = os.path.join(_IMPL_DIR, "config.toml")
_PLANTS_DIR = os.path.join(_IMPL_DIR, "plants")
_SCHEDULES_DIR = os.path.join(_IMPL_DIR, "pump_schedules")


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
    # Check if real MODBUS should be used (configured in config.toml)
    modbus_config = config.get("modbus", {})
    use_real_modbus = modbus_config.get("enabled", False)

    if use_real_modbus:
        print(f"  Using real MODBUS on {modbus_config.get('port', '/dev/ttyUSB0')}")
        busses = com_bus.busses(
            use_real_modbus=True,
            port=modbus_config.get("port", "/dev/ttyUSB0"),
            baudrate=modbus_config.get("baudrate", 9600),
            parity=modbus_config.get("parity", "N"),
            timeout=modbus_config.get("timeout", 1.0)
        )
    else:
        print("  Using dummy busses (set modbus.enabled=true in config for real hardware)")
        busses = com_bus.busses()

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
                busses=busses,
                schedules_directory=_SCHEDULES_DIR
            )
        )
    print("Units done!")

    print("Spinning up web API")
    api = web_api.WebAPI(
        host="0.0.0.0",
        port=8099,
        db_client=db.spawn_client(),
        units=units
    )

    async with anyio.create_task_group() as tg:
        tg.start_soon(api.start)
        for unit in units:
            tg.start_soon(unit.start_sensing)
            if isinstance(unit, plant.Plant):
                tg.start_soon(unit.start_watering)
    