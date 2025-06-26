import adafruit_sht4x
import adafruit_tca9548a
from adafruit_as7341 import AS7341
import time

from config import (
    precision_map,
    get_sht45_port,
    get_sht45_mode,
    get_as7341_port,
    get_reinit_timeout,
)

def init_as7341(tca: adafruit_tca9548a.TCA9548A) -> AS7341:
    """Initialize the AS7341 light sensor."""

    # Get the port number for the AS7341 sensor
    port_as7341 = get_as7341_port()

    try:
        return AS7341(tca[port_as7341])
    except ValueError as e:
        print(f"[ValueError] initializing AS7341 sensor: {e}")
        return None
    
timeout_seconds = get_reinit_timeout()
    
def init_read_as7341(tca: adafruit_tca9548a.TCA9548A) -> callable: 
    """Return a closure that checks for a timeout and raises TimeoutError."""
    last_time = [time.monotonic()]  # Mutable container to allow updates

    def check_timeout() -> None:
        current_time = time.monotonic()
        if current_time - last_time[0] > timeout_seconds:
            last_time[0] = current_time  # Reset timer after timeout
            return init_as7341

    return check_timeout

def read_as7341(light_sensor: AS7341) -> dict: #reutrns a tuple with dict and valid reaing.
    """Get the light sensor readings from the AS7341 sensor."""
    if light_sensor is None:
        return {
            "name": "as7341",
            "violet": -1,
            "indigo": -1,
            "blue": -1,
            "cyan": -1,
            "green": -1,
            "yellow": -1,
            "orange": -1,
            "red": -1,
            "status": "disconnected",
        }

    try:
        # Read the light sensor values
        measurements = {
            "name": "as7341",
            "violet": light_sensor.channel_415nm,
            "indigo": light_sensor.channel_445nm,
            "blue": light_sensor.channel_480nm,
            "cyan": light_sensor.channel_515nm,
            "green": light_sensor.channel_555nm,
            "yellow": light_sensor.channel_590nm,
            "orange": light_sensor.channel_630nm,
            "red": light_sensor.channel_680nm,
            "status": "connected",
        }
        return measurements
    except OSError as e:
        print(f"Error reading from AS7341 sensor: {e}")
        value = retinit_as7341(light_sensor)  # Reinitialize the sensor if there's an error
        return {
            "name": "as7341",
            "violet": -1,
            "indigo": -1,
            "blue": -1,
            "cyan": -1,
            "green": -1,
            "yellow": -1,
            "orange": -1,
            "red": -1,
            "status": "disconnected",
        }

def init_sht45(tca: adafruit_tca9548a.TCA9548A) -> adafruit_sht4x.SHT4x:
    """Initialize the SHT45 temperature and humidity sensor."""

    # Get the port for the SHT45 sensor
    port_sht45 = get_sht45_port()

    # Get the mode string for the SHT45 sensor
    mode_str_sht45 = get_sht45_mode()

    try:
        # SHT45 is a temperature and humidity sensor
        sht45 = adafruit_sht4x.SHT4x(tca[port_sht45])

        if mode_str_sht45 in precision_map:
            # Set the sensor mode based on the string value
            mode_value = precision_map[mode_str_sht45]
            sht45.mode = mode_value
        else:
            raise ValueError(f"Invalid mode string: {mode_str_sht45}")

        # Can also set the mode to enable heater
        # sht45.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
        print("Current mode for SHT45 is: ", adafruit_sht4x.Mode.string[sht45.mode])

        return sht45
    except ValueError as e:
        print(f"[ValueError] initializing SHT45 sensor: {e}")
        return None

def read_sht45(sht45: adafruit_sht4x.SHT4x) -> dict:
    """Get the temperature and humidity readings from the SHT45 sensor."""
    if sht45 is None:
        return {
            "name": "sht45",
            "temperature": -1.,
            "relative_humidity": -1.,
            "status": "disconnected",
        }

    try:
        temperature, relative_humidity = sht45.measurements
        return {
            "name": "sht45",
            "temperature": temperature,
            "relative_humidity": relative_humidity,
            "status": "connected",
        }
    except OSError as e:
        print(f"[OSError] reading from SHT45 sensor: {e}")
        return {
            "name": "sht45", 
            "temperature": -1., 
            "relative_humidity": -1., 
            "status": "disconnected",
        }

def print_sht45_measurements(measurements: dict) -> None:
    """Print the SHT45 temperature and humidity measurements."""
    temperature_str = f"{measurements['temperature']:.1f}"
    humidity_str = f"{measurements['relative_humidity']:.1f}"

    print(f"SHT45 --> Temperature: {temperature_str} C, Humidity: {humidity_str} %")


def print_as7341_measurements(measurements: dict) -> None:
    """Print the AS7341 light sensor measurements."""
    violet_str = f"{measurements['violet']:.1f}"
    indigo_str = f"{measurements['indigo']:.1f}"
    blue_str = f"{measurements['blue']:.1f}"
    cyan_str =  f"{measurements['cyan']:.1f}"
    green_str = f"{measurements['green']:.1f}"
    yellow_str = f"{measurements['yellow']:.1f}"
    orange_str = f"{measurements['orange']:.1f}"
    red_str = f"{measurements['red']:.1f}"

    print("AS7341 light sensor: 415nm wavelength (Violet)  %s" % violet_str)
    print("AS7341 light sensor: 445nm wavelength (Indigo) %s" % indigo_str)
    print("AS7341 light sensor: 480nm wavelength (Blue)   %s" % blue_str)
    print("AS7341 light sensor: 515nm wavelength (Cyan)   %s" % cyan_str)
    print("AS7341 light sensor: 555nm wavelength (Green)   %s" % green_str)
    print("AS7341 light sensor: 590nm wavelength (Yellow)  %s" % yellow_str)
    print("AS7341 light sensor: 630nm wavelength (Orange)  %s" % orange_str)
    print("AS7341 light sensor: 680nm wavelength (Red)     %s" % red_str)
