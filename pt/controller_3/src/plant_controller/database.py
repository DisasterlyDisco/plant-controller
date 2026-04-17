from influxdb_client_3 import Point, InfluxDBClient3
from . import datapoint
    
class DatabaseClient(InfluxDBClient3):
    def write_measurement(
        self,
        physical_unit: str,
        datapoint: datapoint.Datapoint
    ):
        self.write(
            Point(
                Database.format_for_table_name(
                    physical_unit,
                    datapoint.parameter
                )
            ).tag("physical_unit", physical_unit)
             .tag("parameter", datapoint.parameter)
             .field("value", datapoint.value)
             .field("confidence", str(datapoint.confidence))
             .field("units", datapoint.units)
        )
    
    def read_all(
        self,
        physical_unit: str,
        parameter: str   
    ):
        return self.query(
            f'SELECT * FROM '
            + Database.format_for_table_name(
                physical_unit,
                parameter
            )
        ).to_pandas()

class Database:
    def __init__(
        self,
        token: str,
        name: str = 'plant-controller',
        host: str = 'http://127.0.0.1:8181',
    ):
        self.token=token
        self.name=name
        self.host=host

    def exists(self) -> bool:
        return True
    
    def initialize(self):
        pass

    def spawn_client(self) -> DatabaseClient:
        return DatabaseClient(
            host=self.host,
            database=self.name,
            token=self.token
        )
    
    def format_for_table_name(physical_unit: str, parameter: str) -> str:
        return f'{physical_unit}_{parameter}'.lower()
