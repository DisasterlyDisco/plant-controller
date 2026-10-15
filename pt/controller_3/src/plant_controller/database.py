"""Database access layer for the plant controller.

Wraps InfluxDB client functionality, providing methods to write sensor
measurements and watering events, and to query historical data.
"""

import logging
_logger = logging.getLogger(__name__)

from datetime import datetime
import os

from influxdb_client_3 import InfluxDBClient3

from .datapoint import Datapoint


class DatabaseClient(InfluxDBClient3):
    """Extended InfluxDB client with convenience methods for plant data.

    Inherits from InfluxDBClient3 and adds domain-specific read/write
    methods that work with Datapoint objects.
    """

    def write_measurements(
        self,
        physical_unit: str,
        data: Datapoint | list[Datapoint]
    ):
        """Write one or more datapoints to the database.

        Args:
            physical_unit: Name of the unit (used for table naming).
            data: A single Datapoint or list of Datapoints to persist.
        """
        _logger.debug(f"Writing point for unit: {physical_unit}")
        try:
            if isinstance(data, Datapoint):
                point = data.to_point(physical_unit)
                _logger.debug(f"Writing single point: {point}")
                self.write(point)
            else:
                points = [dp.to_point(physical_unit) for dp in data]
                _logger.debug(f"Writing multiple points: {points}")
                self.write(points)
        except Exception as e:
            _logger.error(f"Failed to write point(s) for unit {physical_unit}: {e}", exc_info=True)
            raise e

    def read_measurements(
        self,
        physical_unit: str,
        parameter: str,
        limit: int | None = None,
        since_timestamp: datetime | None = None
    ):
        """Query historical measurements from the database.

        Args:
            physical_unit: Name of the unit to query.
            parameter: Parameter name (e.g. 'temperature', 'watering').
            limit: Maximum number of records to return (most recent first).
            since_timestamp: Only return records after this time.

        Returns:
            A pandas DataFrame of matching records, ordered by time descending.
        """
        query = (
            f'SELECT * FROM ' + Datapoint.format_for_table_name(
                physical_unit,
                parameter
            )
            + (f" WHERE time > '{since_timestamp.isoformat()}'" if since_timestamp else '')
            + f' ORDER BY time DESC'
            + (f' LIMIT {limit}' if limit else '')
        )
        _logger.debug(f'Executing query: {query}')
        return self.query(
            query
        ).to_pandas()

    def interactive_export_database(self):
        """Export the entire database to a file interactively."""
        from .cli_helpers import CANCELLATION_KEYWORDS, clear_screen

        clear_screen()

        while(1):
            export_dir = input("Enter the directory in which to save the exported database (or 'quit' to cancel): ")
            clear_screen()

            if export_dir.lower() in CANCELLATION_KEYWORDS:
                print("Export cancelled.")
                return

            if not export_dir:
                export_dir = os.getcwd()
            elif not os.path.exists(export_dir):
                os.makedirs(export_dir)

            confirm = input(f"Are you sure you want to export the entire database to {export_dir}? (yes/NO): ")
            clear_screen()
            if confirm.lower() in ['yes', 'y']:
                break
            elif confirm.lower() in CANCELLATION_KEYWORDS:
                print("Export cancelled.")
                return

        while(1):
            print("Select the export format:")
            print("CSV")
            print("JSON")
            print("Parquet")
            format = input().lower()
            clear_screen()
            if format in ['csv', 'json', 'parquet']:
                break
            elif format in CANCELLATION_KEYWORDS:
                print("Export cancelled.")
                return
            else:
                print(f"Invalid selection: {format}. Please choose CSV, JSON, or Parquet.")

        tables = self.query('SHOW TABLES').to_pandas()
        if tables.empty:
            print("No tables found in the database. Export aborted.")
            return
        
        _logger.debug(f"Found tables: {tables}")

        print(f"Exporting database as {format.upper()} file, please be patient...")
        for _, table in tables.iterrows():
            if table["table_schema"] != "iox":
                break  # Only export tables from the 'iox' schema, as these are the ones created by the plant controller
            table_name = table["table_name"]
            print(f"Exporting table: {table_name}...", end="", flush=True)
            result = self.query(f'SELECT * FROM "{table_name}"').to_pandas()
            if result.empty:
                _logger.warning(f"No data found in table {table_name}. Skipping export for this table.")
                continue

            table_export_path = os.path.join(export_dir, f"{table_name}.{format}")
            match format:
                case 'csv':
                    result.to_csv(table_export_path, index=False)
                case 'json':
                    result.to_json(table_export_path, orient='records', lines=True)
                case 'parquet':
                    result.to_parquet(table_export_path, index=False)
            print("Done!")

        clear_screen()
        print(f"Database exported successfully! All tables have been saved to {export_dir}.")


class Database:
    """Database connection configuration and client factory.

    Attributes:
        token: Authentication token for InfluxDB.
        name: Database (bucket) name.
        host: InfluxDB host URL.
    """

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
        """Check if the database exists (currently always returns True)."""
        return True

    def initialize(self):
        """Initialize the database (no-op, reserved for future use)."""
        pass

    def spawn_client(self) -> DatabaseClient:
        """Create and return a new DatabaseClient connected to this database."""
        return DatabaseClient(
            host=self.host,
            database=self.name,
            token=self.token
        )
