"""HTTP API for the plant controller.

Provides a FastAPI-based REST interface for:
    - Querying sensor measurements (``/sensing/{unit}/{parameter}``)
    - Viewing watering events (``/actuation/{unit}/watering_events``)
    - Inspecting and updating pump schedules
    - Listing available units and their capabilities
"""

from typing import Any, Annotated
from datetime import datetime

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from .database import DatabaseClient
from .unit import Unit
from ._version import __version__


class ScheduleJSON(BaseModel):
    """Request body model for schedule update endpoints."""
    type: str
    schedule: Any

    def to_dict(self) -> dict[str, Any]:
        """Convert to a canonical plain dict."""
        return {
            "type": self.type,
            "schedule": self.schedule
        }


class WebAPI:
    """HTTP API server wrapping the plant controller's data and commands.

    Attributes:
        host: Bind address for the HTTP server.
        port: Port number for the HTTP server.
        db_client: Database client for reading historical data.
        sensed_units: Dict of all units (keyed by name).
        actuated_units: Dict of units with actuation (keyed by name).
        server: The uvicorn server instance.
    """
    def __init__(
        self,
        host: str,
        port: int,
        db_client: DatabaseClient,
        units: list[Unit],
        log_level: str = "INFO"
    ):
        """Initialize the web API and define all routes.

        Args:
            host: IP address to bind to (e.g. '0.0.0.0').
            port: TCP port number.
            db_client: Database client for querying measurements.
            units: List of all Unit instances to expose.
            log_level: Logging level for uvicorn (default: 'INFO').
        """
        self.host = host
        self.port = port
        self.db_client = db_client
        self.sensed_units = {unit.name: unit for unit in units}
        self.actuated_units = {unit.name: unit for unit in units if unit.has_actuation()}
        self.log_level = log_level

        api = FastAPI(
            title="Plant Controller web API",
            description="Fetch measurements, get overviews of plants and capabilities, and update the Controllers watering schedule",
            version=__version__
        )
        router = APIRouter()

        def check_unit_in_units(unit: str, units: dict[str, Unit]):
            """Raise 404 if the given unit name is not in the units dict."""
            if unit not in units:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unit '{unit}' not found. Available units: {list(units)}"
                )
        
        def parse_timestamp(timestamp: str) -> datetime:
            """Parse an ISO 8601 timestamp string, raising 400 on failure."""
            try:
                return datetime.fromisoformat(timestamp)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": f"Invalid timestamp format: {e}",
                        "correct_format": "YYYYMMDD-hhmmss.sssssssss",
                        "correct_format_example": "20260528-112233.123456789",
                        "note": "Anything after the date can be ommitted - YYYYMMDD will be parsed as YYYYMMDD-000000.000000000, YYYYMMDD-hh will be parsed as YYYYMMDD-hh0000.000000000, and so on."
                    }
                )

        @router.get("/", include_in_schema=False)
        async def root() -> dict[str, Any]:
            """Return controller version, current time, and docs link."""
            return {
                "plant-controller": {
                    "version": __version__,
                    "current time": datetime.now(),
                    "api docs endpoint": "/docs"
                }
            }
        
        @router.get("/favicon.ico", include_in_schema=False)
        async def dummy_favicon():
            """No-op handler to suppress browser favicon 404s."""
            return
        
        @router.get("/sensing")
        async def sensed_units_overview() -> dict[str, Any]:
            """List all units that have sensors attached."""
            return {"sensed units": list(self.sensed_units)}
        
        @router.get("/sensing/{unit}")
        async def sensed_unit_parameters(unit: str) -> JSONResponse:
            """List the sensed parameters and capabilities for a unit."""
            check_unit_in_units(unit, self.sensed_units)
            return self.sensed_units[unit].get_sensing_capabilites()

        @router.get("/sensing/{unit}/{parameter}")
        async def fetch_measurement(
            unit: str,
            parameter: str,
            limit: Annotated[
                int | None,
                Query(
                    title="Measurement limit",
                    description="The maximum number of measurements to return. If not provided, all measurements will be returned."
                )
            ] = None,
            since_timestamp: Annotated[
                str | None,
                Query(
                    title="Since timestamp",
                    description="Only return measurements taken after this timestamp. If not provided, all measurements will be returned regardless of timestamp. Should be in the format YYYYMMDD-hhmmss.sssssssss, but anything after the date can be ommitted - YYYYMMDD will be parsed as YYYYMMDD-000000.000000000, YYYYMMDD-hh will be parsed as YYYYMMDD-hh0000.000000000, and so on.",
                    examples=["20260528-112233.123456789"]
                )
            ] = None
        ) -> JSONResponse:
            """Fetch measurements for a given unit and parameter.

            Optionally limit the number of results and/or filter by timestamp.
            """
            check_unit_in_units(unit, self.sensed_units)
            if parameter not in self.sensed_units[unit].get_sensing_capabilites():
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Parameter '{parameter}' not found for unit '{unit}'. Available parameters for this unit: {list(self.sensed_units[unit].get_sensing_capabilites())}"}
                )
            if since_timestamp != None:
                since_timestamp = parse_timestamp(since_timestamp)
            return self.db_client.read_measurements(unit, parameter, limit, since_timestamp).to_dict(orient="records")
        
        @router.get("/actuation")
        async def actuated_units_overview() -> dict[str, Any]:
            """List all units that have actuation (pumps) attached."""
            return {"actuated units": list(self.actuated_units)}
        
        @router.get("/actuation/{unit}")
        async def actuated_unit_endpoints(unit: str) -> dict[str, Any]:
            """List available actuation endpoints for a unit."""
            check_unit_in_units(unit, self.actuated_units)
            return {
                "Show watering events": f"/actuation/{unit}/watering_events",
                "Show current watering schedule": f"/actuation/{unit}/show_schedule",
                "Update watering schedule": f"/actuation/{unit}/update_schedule"
            }

        @router.get("/actuation/{unit}/watering_events")
        async def fetch_watering_events(
            unit: str,
            limit: Annotated[
                int | None,
                Query(
                    title="Measurement limit",
                    description="The maximum number of events to return. If not provided, all events will be returned."
                )
            ] = None,
            since_timestamp: Annotated[
                str | None,
                Query(
                    title="Since timestamp",
                    description="Only return events taken after this timestamp. If not provided, all events will be returned regardless of timestamp. Should be in the format YYYYMMDD-hhmmss.sssssssss, but anything after the date can be ommitted - YYYYMMDD will be parsed as YYYYMMDD-000000.000000000, YYYYMMDD-hh will be parsed as YYYYMMDD-hh0000.000000000, and so on.",
                    examples=["20260528-112233.123456789"]
                )
            ] = None
        ):
            """Fetch watering event history for a unit.

            Optionally limit the number of results and/or filter by timestamp.
            """
            check_unit_in_units(unit, self.actuated_units)
            if since_timestamp != None:
                since_timestamp = parse_timestamp(since_timestamp)
            return self.db_client.read_measurements(unit, "watering", limit, since_timestamp).to_dict(orient="records")
        
        @router.get("/actuation/{unit}/show_schedule")
        async def show_watering_schedule(unit: str):
            """Return the current watering schedule for a unit."""
            check_unit_in_units(unit, self.actuated_units)
            return self.actuated_units[unit].schedule.get_schedule()
        
        @router.put("/actuation/{unit}/update_schedule", status_code=204)
        async def update_watering_schedule(unit: str, schedule: ScheduleJSON):
            """Replace the watering schedule for a unit. Returns 204 on success."""
            check_unit_in_units(unit, self.actuated_units)
            try:
                # FastAPI implicitly transforms json request bodies into python dictionaries,
                # so the schedule can be passed on as is.
                self.actuated_units[unit].update_schedule(schedule.to_dict())
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"Schedule wasn't valid: {e}")
        
        @router.get("/actuation/rocket_silo/nuclear_missile/launch", include_in_schema=False)
        async def launch_missile() -> JSONResponse:
            """Easter egg. Returns 418 I'm a teapot."""
            return JSONResponse(
                status_code=418,
                content={"error": "Sorry, but firing nuclear missiles is not conducive to plant health. Please water your plants instead :)"},
            )

        api.include_router(router)

        self.server = uvicorn.Server(
            config=uvicorn.Config(
                api,
                host=self.host,
                port=self.port,
                log_level=self.log_level.lower(),
                loop="anyio"
            )
        )
    
    async def start(self):
        """Start the HTTP server (runs indefinitely)."""
        await self.server.serve()

