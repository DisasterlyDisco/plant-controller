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
    type: str
    schedule: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "schedule": self.schedule
        }

class WebAPI:
    def __init__(
        self,
        host: str,
        port: int,
        db_client: DatabaseClient,
        units: list[Unit],
        log_level: str = "INFO"
    ):
        self.host = host
        self.port = port
        self.db_client = db_client
        self.sensed_units = {unit.name: unit for unit in units}
        self.actuated_units = {unit.name: unit for unit in units if unit.has_actuation()}
        self.log_level = log_level

        api = FastAPI(
            title="Plant Controller web API",
            description="Fetch measurements, get overviews of plants and capabilities, and update the Controllers watering schedule",
        )
        router = APIRouter()

        def check_unit_in_units(unit: str, units: dict[Unit]):
            if unit not in units:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unit '{unit}' not found. Available units: {list(units)}"
                )
        
        def parse_timestamp(timestamp: str) -> datetime:
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

        @router.get("/")
        async def root() -> dict[str, Any]:
            return {
                "plant-controller": {
                    "version": __version__,
                    "current time": datetime.now(),
                    "api docs endpoint": "/docs"
                }
            }
        
        @router.get("/favicon.ico")
        async def dummy_favicon():
            return
        
        @router.get("/sensing")
        async def sensed_units_overview() -> dict[str, Any]:
            return {"sensed units": list(self.sensed_units)}
        
        @router.get("/sensing/{unit}")
        async def sensed_unit_parameters(unit: str) -> JSONResponse:
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
            """
            Fetch measurements for a given physical unit and parameter.
            
            Optionally, limit the number of measurements returned and/or
            only return measurements taken after a certain timestamp.
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
            return {"actuated units": list(self.actuated_units)}
        
        @router.get("/actuation/{unit}")
        async def actuated_unit_endpoints(unit: str) -> dict[str, Any]:
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
            check_unit_in_units(unit, self.actuated_units)
            if since_timestamp != None:
                since_timestamp = parse_timestamp(since_timestamp)
            return self.db_client.read_measurements(unit, "watering", limit, since_timestamp).to_dict(orient="records")
        
        @router.get("/actuation/{unit}/show_schedule")
        async def show_watering_schedule(unit: str):
            check_unit_in_units(unit, self.actuated_units)
            return self.actuated_units[unit].schedule.get_schedule()
        
        @router.put("/actuation/{unit}/update_schedule", status_code=204)
        async def update_watering_schedule(unit: str, schedule: ScheduleJSON):
            check_unit_in_units(unit, self.actuated_units)
            try:
                # FastAPI implicitly transforms json request bodies into python dictionaries,
                # so the schedule can be passed on as is.
                self.actuated_units[unit].update_schedule(schedule.to_dict())
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"Schedule wasn't valid: {e}")
        
        @router.get("/actuation/rocket_silo/nuclear_missile/launch", include_in_schema=False)
        async def launch_missile() -> JSONResponse:
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
        await self.server.serve()

