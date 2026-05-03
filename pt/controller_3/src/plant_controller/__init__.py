import logging
import os
_IMPL_DIR = os.path.expanduser("~/.plant_controller")
_LOG_PATH = os.path.join(_IMPL_DIR, "log")
_CONFIG_PATH = os.path.join(_IMPL_DIR, "config.toml")
_PLANTS_DIR = os.path.join(_IMPL_DIR, "plants")
_SCHEDULES_DIR = os.path.join(_IMPL_DIR, "pump_schedules")

logger = logging.getLogger(__name__)

logging.basicConfig(
    handlers=[
        logging.StreamHandler()
    ],
    level=logging.WARNING,
)

import argparse
import tomllib

import anyio

from . import _version, com_bus, database, greenhouse, plant, unit, web_api
from .cli_helpers import clear_screen

async def controller_run(args: argparse.Namespace):
    print("Starting plant controller...")
    units, db_client, busses = await common_startup_tasks()

    try:
        api = web_api.WebAPI(
            host="0.0.0.0",
            port=8099,
            db_client=db_client,
            units=units,
            log_level=args.log_level
        )

        logger.info("Starting main loop")
        async with anyio.create_task_group() as tg:
            tg.start_soon(api.start)
            for unit in units:
                tg.start_soon(unit.start_sensing)
                if isinstance(unit, plant.Plant):
                    tg.start_soon(unit.start_watering)
            print("Plant controller is now running. Press Ctrl+C to quit.")
    except KeyboardInterrupt:
        logger.info("Got SIGINT, shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        busses[com_bus._MODBUS].close()

async def controller_setup(args: argparse.Namespace):
    clear_screen()
    print("Welcome to the plant controller setup utility.")
    print("Here you are able to perform different setup actions, depending on the connected units and sensors.")
    print("")
    print("Checking connected units and sensors for setup actions...")
    units, _, busses = await common_startup_tasks()
    
    try:
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
                clear_screen()
                print("Exiting setup utility. Goodbye!")
                break
            if "." in choice:
                chosen_unit, chosen_action = choice.split(".", 1)
                if chosen_unit in setup_actions and chosen_action in setup_actions[chosen_unit]:
                    action_info = setup_actions[chosen_unit][chosen_action]
                    clear_screen()
                    print(f"Performing setup action '{choice}'...")
                    await action_info["function"]()
                    continue
            clear_screen()
            print(f"Invalid choice '{choice}'. Please try again.")
                

    except KeyboardInterrupt:
        logger.info("Got SIGINT, shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        busses[com_bus._MODBUS].close()

async def common_startup_tasks():
    logger.info("Performing common startup tasks...")

    if not os.path.exists(_IMPL_DIR):
        logger.info(f"Implementation directory not found at '{_IMPL_DIR}', creating it...")
        os.makedirs(_IMPL_DIR)

    if not os.path.exists(_LOG_PATH):
        logger.info(f"Log file not found at '{_LOG_PATH}', creating it...")
        with open(_LOG_PATH, "w") as f:
            pass

    file_handler = logging.FileHandler(_LOG_PATH)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    if not os.path.exists(_CONFIG_PATH):
        logger.critical(f"Config file not found at '{_CONFIG_PATH}'.")
        exit(1)

    if not os.path.exists(_PLANTS_DIR):
        logger.info(f"Plants directory not found at '{_PLANTS_DIR}', creating it...")
        os.makedirs(_PLANTS_DIR)

    if not os.path.exists(_SCHEDULES_DIR):
        logger.info(f"Pump schedules directory not found at '{_SCHEDULES_DIR}', creating it...")
        os.makedirs(_SCHEDULES_DIR)

    config = load_config()
    db_client = connect_to_db(config)
    busses = await com_bus.busses()
    try:
        units = create_units(
            config=config,
            db_client=db_client,
            busses=busses
        )
        return units, db_client, busses
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        busses[com_bus._MODBUS].close()
        raise

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

    for config, config_location in [
        (plant.Plant.parse_config(os.path.join(_PLANTS_DIR, f)), os.path.join(_PLANTS_DIR, f))
        for f
        in os.listdir(_PLANTS_DIR)
        if f.endswith(".json")
    ]:
        units.append(
            plant.Plant(
                config=config,
                db_client=db_client,
                busses=busses,
                schedules_directory=_SCHEDULES_DIR,
                config_path=config_location
            )
        )

    if not units:
        logger.warning(f"No plants configured for the controller. Add plant configuration files to '{_SCHEDULES_DIR}'.")

    units.append(
        greenhouse.Greenhouse(
            db_client=db_client,
            busses=busses
        )
    )
    
    return units

def connect_to_db(config: dict) -> database.DatabaseClient:
    logger.info(f"Connecting to database {config['database']['name']} at {config['database']['host']}...")
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

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_version.__version__}"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("PLANT_CONTROLLER_LOG_LEVEL", "WARNING").upper(),
        help="Set the logging level. Default is INFO. Can also be set via the PLANT_CONTROLLER_LOG_LEVEL environment variable.",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
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
    logger.setLevel(args.log_level)
    if not hasattr(args, "func"):
        parse_args(["--help"])
        return
    await args.func(args)
    