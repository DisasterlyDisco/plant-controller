import adafruit_sht4x
import yaml

precision_map = {
    "NOHEAT_HIGHPRECISION": adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION,
    "NOHEAT_MEDPRECISION": adafruit_sht4x.Mode.NOHEAT_MEDPRECISION,
    "NOHEAT_LOWPRECISION": adafruit_sht4x.Mode.NOHEAT_LOWPRECISION,
    "HIGHHEAT_1S": adafruit_sht4x.Mode.HIGHHEAT_1S,
    "HIGHHEAT_100MS": adafruit_sht4x.Mode.HIGHHEAT_100MS,
    "MEDHEAT_1S": adafruit_sht4x.Mode.MEDHEAT_1S,
    "MEDHEAT_100MS": adafruit_sht4x.Mode.MEDHEAT_100MS,
    "LOWHEAT_1S": adafruit_sht4x.Mode.LOWHEAT_1S,
    "LOWHEAT_100MS": adafruit_sht4x.Mode.LOWHEAT_100MS,
}

RESTART_DELAY = 5  # restart delay to init sensors


def get_config() -> dict:
    with open("config/config.yaml", "r") as file:
        data = yaml.safe_load(file)
    return data


def get_sensor_sampling_period() -> int:
    config = get_config()
    return config["plant"]["sensors"]["sampling_period"]


def get_actuator_shedule(pump_key: str) -> dict:
    config = get_config()
    actuators = config["plant"]["actuators"]
    return actuators[pump_key]["schedule"]


def get_moisture_sensor_port(sensor_key: str) -> int:
    """
    Returns the port number for a given moisture sensor key (e.g., 'moisture_0').
    """
    config = get_config()
    seesaw = config["plant"]["sensors"]["seesaw"]
    return seesaw[sensor_key]["port"]


def get_moisture_sensor_addr(sensor_key: str) -> int:
    """
    Returns the I2C address for a given moisture sensor key (e.g., 'moisture_0').
    """
    config = get_config()
    seesaw = config["plant"]["sensors"]["seesaw"]
    return seesaw[sensor_key]["addr"]


def get_sht45_port() -> int:
    """
    Returns the port number for the SHT45 sensor.
    """
    config = get_config()
    return config["plant"]["sensors"]["sht45"]["port"]


def get_sht45_mode() -> str:
    """
    Returns the mode string for the SHT45 sensor.
    """
    config = get_config()
    return config["plant"]["sensors"]["sht45"]["mode"]


def get_as7341_port() -> int:
    """
    Returns the port number for the AS7341 sensor.
    """
    config = get_config()
    return config["plant"]["sensors"]["as7341"]["port"]


def get_stomp_url() -> str:
    config = get_config()
    return config["services"]["external"]["stomp"]["url"]


def get_stomp_user() -> str:
    config = get_config()
    return config["services"]["external"]["stomp"]["user"]


def get_stomp_password() -> str:
    config = get_config()
    return config["services"]["external"]["stomp"]["pass"]


def get_stomp_port() -> int:
    config = get_config()
    return config["services"]["external"]["stomp"]["port"]


def get_relay_by_pump_id(pump_id: str) -> str:
    """
    Returns the relay name (e.g., 'one') for a given pump_id (e.g., 'pump_1').
    """
    config = get_config()
    actuators = config["plant"]["actuators"]
    if pump_id in actuators:
        return actuators[pump_id]["relay"]
    raise ValueError(f"No relay found for pump_id: {pump_id}")


def get_STOMP_destination_topics() -> list:
    """
    Returns a list of STOMP destination topics for all actuators.
    """
    config = get_config()
    topics = config["services"]["external"]["stomp"]["topics"]
    return [key for key in topics.keys()]


def get_pump_id_by_topic(topic: str) -> str:
    """
    Returns the pump_id for a given STOMP topic.
    """
    config = get_config()
    topics = config["services"]["external"]["stomp"]["topics"]
    if topic in topics:
        return topics[topic]
    raise ValueError(f"No pump_id found for topic: {topic}")


def get_pump_config(pump_id: str) -> dict:
    """
    Returns the configuration for a given pump_id.
    """
    config = get_config()
    actuators = config["plant"]["actuators"]
    if pump_id in actuators:
        return actuators[pump_id]
    raise ValueError(f"No configuration found for pump_id: {pump_id}")


def get_moisture_sensors() -> dict:
    """
    Returns the configuration for all moisture sensors.
    """
    config = get_config()
    return config["plant"]["sensors"]["seesaw"]

def get_reinit_timeout() -> float:
    """
    Returns the timeout value for reinitializing sensors.
    """
    config = get_config()
    return config["plant"]["sensors"]["reinit_timeout_seconds"]
