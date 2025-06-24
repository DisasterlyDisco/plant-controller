import urllib3
import socket
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
import yaml
import ssl
import requests


class InfluxDBStore:
    def __init__(self):
        config = self.get_config()
        config = config["services"]["internal"]["influxdb"]
        self._org = config["org"]
        self._url = config["url"]
        self._token = config["token"]
        self._bucket = config["bucket"]
        # print(self._org, self._url, self._token, self._bucket)
        write_client = InfluxDBClient(url=self._url, token=self._token, org=self._org)
        self._write_api = write_client.write_api(write_options=SYNCHRONOUS)

    def get_config(self) -> dict:
        with open("config/config.yaml", "r") as file:
            data = yaml.safe_load(file)
        return data

    def write(self, record: Point) -> None:
        """
        Write a single data point to InfluxDB.
        """
        try:
            self._write_api.write(bucket=self._bucket, org=self._org, record=record)
            print(
                f"Successfully wrote point '{record.to_line_protocol()}' to the bucket {self._bucket}."
            )
        except InfluxDBError as e:
            print(
                f"[InfluxDB Error] Failed to write point '{record.to_line_protocol()}' with exception: {e.message}"
            )
            print(f"[InfluxDB Error] Error Status Code: {e.status}")
            print(f"[InfluxDB Error] Error Message: {e.body}")
            print(f"[InfluxDB Error] Error Headers: {e.headers}")
        except urllib3.exceptions.ConnectTimeoutError as e:
            print(
                f"[Connection Timeout Error] Failed to write point '{record.to_line_protocol()}' with exception ConnectTimeoutError: {e}"
            )
        except urllib3.exceptions.NewConnectionError as e:
            print(
                f"[NewConnection Error] Failed to write point '{record.to_line_protocol()}' with exception NewConnectionError: {e}"
            )
        except urllib3.exceptions.ProtocolError as e:
            print(
                f"[Protocol Error] Failed to write point '{record.to_line_protocol()}' with exception ProtocolError: {e}"
            )
        except urllib3.exceptions.HTTPError as e:
            print(
                f"[HTTP Error] Failed to write point '{record.to_line_protocol()}' with exception HTTPError (generic): {e}"
            )
        except socket.gaierror as e:
            print(
                f"[DNS Error] Failed to write point '{record.to_line_protocol()}' with exception socket.gaierror (DNS resolution): {e}"
            )
        except socket.timeout as e:
            print(
                f"[Timeout Error] Failed to write point '{record.to_line_protocol()}' with exception socket.timeout: {e}"
            )
        except (ssl.SSLError, requests.exceptions.SSLError) as e:
            print(
                f"[SSL/TLS Error] Failed to write point '{record.to_line_protocol()}' with exception {type(e).__name__}: {e}"
            )
        except ValueError as e:
            print(f"[ValueError] Failed to write point: {e}")


def create_point(measurements: dict) -> Point:
    """Create a point for the measurement.
    Args:
        measurements (dict): A dictionary containing the measurement data.
        The dictionary should have a "name" key for the measurement name
        and other keys for the measurement fields.
    Returns:
        Point: An InfluxDB Point object with the measurement data.
    """
    point = Point(measurements.pop("name"))
    for key, value in measurements.items():
        if key != "status":
            point.field(key, value)
        else:
            point.tag(key, value)
    return point


def create_exception_point(e: Exception) -> Point:
    """Create a point for the exception measurement."""
    point = Point("exception").field("status", 0)
    return point
