import logging
import os
logger = logging.getLogger(__name__)
logging.basicConfig(
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser("~/.plant_controller/log"))
    ],
    level=logging.WARNING
)
logging.Formatter("%(asctime)s - [%(levelname)s] %(message)s")

import argparse
import tomllib

import anyio

from . import com_bus, database, greenhouse, plant, unit, web_api

_IMPL_DIR = os.path.abspath("../impl")
_CONFIG_PATH = os.path.join(_IMPL_DIR, "config.toml")
_PLANTS_DIR = os.path.join(_IMPL_DIR, "plants")
_SCHEDULES_DIR = os.path.join(_IMPL_DIR, "pump_schedules")

async def controller_run(args: argparse.Namespace):
    config = load_config()
    db_client = connect_to_db(config)
    busses = await com_bus.busses()
    try:
        units = create_units(
            config=config,
            db_client=db_client,
            busses=busses
        )
        api = web_api.WebAPI(
            host="0.0.0.0",
            port=8099,
            db_client=db_client,
            units=units
        )

        logger.info("Starting main loop")
        async with anyio.create_task_group() as tg:
            tg.start_soon(api.start)
            for unit in units:
                tg.start_soon(unit.start_sensing)
                if isinstance(unit, plant.Plant):
                    tg.start_soon(unit.start_watering)
    except KeyboardInterrupt:
        logger.info("Got SIGINT, shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        busses[com_bus._MODBUS].close()

async def controller_setup(args: argparse.Namespace):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Welcome to the plant controller setup utility.")
    print("Here you are able to perform different setup actions, depending on the connected units and sensors.")
    print("")
    print("Checking connected units and sensors for setup actions...")
    config = load_config()
    db_client = connect_to_db(config)
    busses = await com_bus.busses()
    try:
        units = create_units(
            config=config,
            db_client=db_client,
            busses=busses
        )
        setup_actions = {}
        for unit in units:
            unit_setup_functions = unit.setup_functions()
            if unit_setup_functions:
                setup_actions[unit.name] = unit_setup_functions
        
        if not setup_actions:
            print("The connected units and sensors do not have any setup actions.")
            print("The setup utility will now exit.")
            return

        while True:
            print("")
            print("Available setup actions:")
            for unit_name, actions in setup_actions.items():
                for action_name, action_info in actions.items():
                    print(f"  {unit_name}.{action_name}: {action_info['description']}")
            print("  exit: Exit the setup utility.")
            print("")
            choice = input("Enter the name of the setup action you want to perform: ")
            if choice == "exit":
                os.system('cls' if os.name == 'nt' else 'clear')
                print("Exiting setup utility. Goodbye!")
                break
            if "." in choice:
                chosen_unit, chosen_action = choice.split(".", 1)
                if chosen_unit in setup_actions and chosen_action in setup_actions[chosen_unit]:
                    action_info = setup_actions[chosen_unit][chosen_action]
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"Performing setup action '{choice}'...")
                    await action_info["function"]()
                    continue
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"Invalid choice '{choice}'. Please try again.")
                

    except KeyboardInterrupt:
        logger.info("Got SIGINT, shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        busses[com_bus._MODBUS].close()

def load_config(path: str = _CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        config = tomllib.load(f)
    return config

def create_units(
    config: dict,
    db_client: database.DatabaseClient,
    busses: dict[str, com_bus.Bus]
) -> list[unit.Unit]:
    units = []
    units.append(
        greenhouse.Greenhouse(
            db_client=db_client,
            busses=busses
        )
    )

    for config in plant_configs():
        units.append(
            plant.Plant(
                config=config,
                db_client=db_client,
                busses=busses,
                schedules_directory=_SCHEDULES_DIR
            )
        )
    
    return units

def plant_configs(path: str = _PLANTS_DIR) -> list[dict]:
    return [
        plant.Plant.parse_config(os.path.join(path, f))
        for f
        in os.listdir(path)
        if f.endswith(".json")
    ]

def connect_to_db(config: dict) -> database.DatabaseClient:
    db = database.Database(
        name=config["database"]["name"],
        host=config["database"]["host"],
        token=config["database"]["token"]
    )
    return db.spawn_client()

def parse_args(*args, **kwargs) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="plant_controller",
        description="System for mointoring and watering of plants."
    )

    subparsers = parser.add_subparsers(
        title='subcommands',
        description='Valid subcommands'
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run the plant controller."
    )
    run_parser.set_defaults(func=controller_run)

    setup_parser = subparsers.add_parser(
        "setup",
        help="Enter setup mode. Setup mode allows for peripheral calibration and other one-time setup tasks."
    )
    setup_parser.set_defaults(func=controller_setup)
    
    return parser.parse_args(*args, **kwargs)

async def main():
    args = parse_args()
    if not hasattr(args, "func"):
        parse_args(["--help"])
        return
    await args.func(args)
    