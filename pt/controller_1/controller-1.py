from datetime import datetime
from schedule import every
import schedule

import adafruit_tca9548a
import board
import time
from typing import Sequence, Any

from store import InfluxDBStore, create_point, create_exception_point

from config import (
    precision_map,
    get_sensor_sampling_period,
    get_actuator_shedule,
    RESTART_DELAY,
)
from pump import (
    water_plant,
    water_plant_1,
    water_plant_2,
    water_plant_3,
)
from sensors.moisture import (
    init_moisture_sensors,
    read_moisture_sensor,
    print_soil_sensor_measurements,
)
from sensors.environment import (
    print_sht45_measurements,
    print_as7341_measurements,
)
from sensors.environment import (
    read_as7341,
    read_sht45,
    init_sht45,
    init_as7341,
)

store_influx = InfluxDBStore()

from comm.stomp import stompClient


def initialise() -> Sequence[Any]:
    """Initializes the sensor objects for the TCA9548A multiplexer."""

    # Create I2C bus as normal
    i2c = board.I2C()  # uses board.SCL and board.SDA

    # Create the TCA9548A object and give it the I2C bus
    tca = adafruit_tca9548a.TCA9548A(i2c)

    # For each sensor, create it using the TCA9548A channel instead of the I2C object
    # moisture sensor with temperature sensing capabilities
    moisture_sensors = init_moisture_sensors(tca)

    # SHT45 is a temperature and humidity sensor
    sht45 = init_sht45(tca)

    # AS7341 is a ten-channel (eight color) light sensor
    light_sensor = init_as7341(tca)

    return moisture_sensors, sht45, light_sensor


def initialise_actuators() -> None:
    """Initializes the actuators."""

    # Get actuator configuration from the config file
    schedule_pump_1 = get_actuator_shedule(pump_key="pump_1")
    schedule_pump_2 = get_actuator_shedule(pump_key="pump_2")
    schedule_pump_3 = get_actuator_shedule(pump_key="pump_3")

    # Set the schedule for the actuators
    if schedule_pump_1:
        every().monday.at(schedule_pump_1).do(lambda: water_plant_1(store_influx))
        every().wednesday.at(schedule_pump_1).do(lambda: water_plant_1(store_influx))
        every().friday.at(schedule_pump_1).do(lambda: water_plant_1(store_influx))
    if schedule_pump_2:
        # Set the schedule for pump 2
        every().day.at(schedule_pump_2).do(lambda: water_plant_2(store_influx))
    if schedule_pump_3:
        # Set the schedule for pump 3
        every().monday.at(schedule_pump_3).do(lambda: water_plant_3(store_influx))
        every().wednesday.at(schedule_pump_3).do(lambda: water_plant_3(store_influx))
        every().friday.at(schedule_pump_3).do(lambda: water_plant_3(store_influx))


def readings(moisture_sensors, sht45, light_sensor):
    print(f"Sample at: {datetime.now().isoformat()}")
    # Create a dict from the measurements
    measurements = read_as7341(sht45)
    print_sht45_measurements(measurements)
    point = create_point(measurements.copy())
    store_influx.write(point)
    # Invlaid readings should mean init again.

    # Create a dict from the measurements
    measurements = read_sht45(light_sensor)
    print_as7341_measurements(measurements)
    point = create_point(measurements.copy())
    store_influx.write(point)

    # Iterate over the moisture sensors and get their readings
    # moisture_sensors is a dict with the sensor name as key and Seesaw object as value
    for moisture_sensor_name, moisture_sensor_value in moisture_sensors.items():
        moisture_reading, temperature_reading = read_moisture_sensor(
            moisture_sensor_value
        )
        # Create a dict from the measurements
        measurements = {
            "name": moisture_sensor_name,
            "moisture": moisture_reading,
            "temperature": temperature_reading,
            "status": "connected" if moisture_sensor_value is not None else "disconnected",
        }
        point = create_point(measurements.copy())
        print_soil_sensor_measurements(measurements)

        store_influx.write(point)

    print("")


if __name__ == "__main__":
    # Initialize the actuators
    initialise_actuators()
    # Initialize the sensors
    moisture_sensors, sht45, light_sensor = initialise()

    # reading interval
    # Set up schedule for sensors
    sampling_period = get_sensor_sampling_period()
    if sampling_period:
        pass
    else:
        raise ValueError(
            f"No sampling_period given in config file for sensors: {sampling_period}"
        )

    # Create STOMP client
    stomp_client = stompClient(
        lambda relay, duration, pump_id: water_plant(
            store_influx=store_influx, pump_id=pump_id, relay=relay, duration=duration
        )
    )

    print("init done")

    while True:
        try:
            readings(moisture_sensors, sht45, light_sensor)

            # time.sleep(5)
            # raise Exception("I2C device error")

        except Exception as e:
            time.sleep(RESTART_DELAY)
            moisture_sensors, sht45, light_sensor = initialise()
            print(f"Exception at: {datetime.now().isoformat()}")

            point = create_exception_point(e)
            store_influx.write(record=point)
            continue

        # water the plants if needed
        schedule.run_pending()
        time.sleep(sampling_period)
