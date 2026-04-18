import uvicorn
from fastapi import FastAPI, APIRouter, Query
from fastapi.responses import JSONResponse
from pandas import DataFrame

from .database import Database

from typing import Dict, Any, Annotated
from datetime import datetime

class WebAPI:
    def __init__(self, host: str, port: int, database: Database):
        self.host = host
        self.port = port
        self.database = database
        self.api = FastAPI(
            title="Plant Controller web API",
            description="Fetch measurements, get overviews of plants and capabilities, and update the Controllers watering schedule",
        )

        router = APIRouter()

        @router.get("/")
        async def root() -> Dict[str, Any]:
            return {
                "welcome": "CONGRATULATIONS - YOU MADE IT :D",
                "a number": 6
            }
        
        @router.get("/sensing/{unit}/{parameter}")
        async def fetch(
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
                    description="Only return measurements taken after this timestamp. If not provided, all measurements will be returned regardless of timestamp.",
                    pattern="^\\d{8}(-\\d{6}(\\.\\d{1,9})?)?$",
                    example="20260528-112233.123456789"
                )
            ] = None
        ) -> JSONResponse:
            if since_timestamp != None:
                try:
                    since_timestamp = datetime.fromisoformat(since_timestamp)
                except Exception as e:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": f"Invalid timestamp format: {e}",
                            "correct_format": "YYYYMMDD-hhmmss.sssssssss",
                            "correct_format_example": "20260528-112233.123456789",
                            "note": "Anything after the date can be ommitted - YYYYMMDD will be parsed as YYYYMMDD-000000.000000000, YYYYMMDD-hh will be parsed as YYYYMMDD-hh0000.000000000, and so on."
                        }
                    )
            client = self.database.spawn_client()
            dataframe = client.read_measurements(unit, parameter, limit, since_timestamp)
            return dataframe.to_dict(orient="records")
        
        @router.get("/acutators/rocket_silo/nuclear_missile/launch")
        async def launch_missile() -> JSONResponse:
            return JSONResponse(
                status_code=418,
                content={"error": "Sorry, but firing nuclear missiles is not conducive to plant health. Please water your plants instead :)"},
            )

        self.api.include_router(router)
    
    def start(self):
        uvicorn.run(
            self.api,
            host=self.host,
            port=self.port
        )

