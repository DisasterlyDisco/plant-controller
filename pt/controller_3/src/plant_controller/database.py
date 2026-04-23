from datetime import datetime

from influxdb_client_3 import InfluxDBClient3

from .datapoint import Datapoint
    
class DatabaseClient(InfluxDBClient3):
    def write_measurements(
        self,
        physical_unit: str,
        data: Datapoint | list[Datapoint]
    ):
        if isinstance(data, Datapoint):
            self.write(data.to_point(physical_unit))
        else:
            self.write([dp.to_point(physical_unit) for dp in data])

    def read_measurements(
        self,
        physical_unit: str,
        parameter: str,
        limit: int | None = None,
        since_timestamp: datetime | None = None
    ):
        query = (
            f'SELECT * FROM ' + Datapoint.format_for_table_name(
                physical_unit,
                parameter
            )
            + (f" WHERE time > '{since_timestamp.isoformat()}'" if since_timestamp else '')
            + f' ORDER BY time DESC'
            + (f' LIMIT {limit}' if limit else '')
        )
        print(f'Executing query: {query}')
        return self.query(
            query
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
