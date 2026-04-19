from datetime import datetime

from influxdb_client_3 import Point, InfluxDBClient3

from .datapoint import Datapoint
    
class DatabaseClient(InfluxDBClient3):
    def write_measurements(
        self,
        physical_unit: str,
        data: Datapoint | list[Datapoint]
    ):
        if isinstance(data, Datapoint):
            self.write(DatabaseClient.datapoint_to_point(physical_unit, data))
        else:
            self.write([DatabaseClient.datapoint_to_point(physical_unit, dp) for dp in data])

    def read_measurements(
        self,
        physical_unit: str,
        parameter: str,
        limit: int | None = None,
        since_timestamp: datetime | None = None
    ):
        query = f'SELECT * FROM ' + Database.format_for_table_name(
                physical_unit,
                parameter
            ) + (f" WHERE time > '{since_timestamp.isoformat()}'" if since_timestamp else '') + f' ORDER BY time DESC' + (f' LIMIT {limit}' if limit else '')
        print(f'Executing query: {query}')
        return self.query(
            query
        ).to_pandas()
    
    @staticmethod
    def datapoint_to_point(physical_unit: str, datapoint: Datapoint) -> Point:
        return Point(
            Database.format_for_table_name(
                physical_unit,
                datapoint.parameter
            )
        ).tag("physical_unit", physical_unit
        ).tag("parameter", datapoint.parameter
        ).field("value", datapoint.value
        ).field("confidence", str(datapoint.confidence)
        ).field("units", datapoint.units)

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
