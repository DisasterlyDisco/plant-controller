import uvicorn
from fastapi import FastAPI, APIRouter, Query
from fastapi.responses import JSONResponse
from pandas import DataFrame

from .database import Database

from typing import Dict, Any, Annotated

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
                    description="The maximum number of measurements to return. If not provided, all measurements will be returned."
                )
            ] = None,
            since_timestamp: Annotated[
                str | None,
                Query(
                    description="Only return measurements taken after this timestamp. If not provided, all measurements will be returned regardless of timestamp."
                )
            ] = None
        ) -> JSONResponse:
            #if since_timestamp != None:
            #    try:
            #        DataFrame([since_timestamp], columns=["timestamp"], dtype="datetime64[ns]")
            #    except Exception as e:
            #        return JSONResponse(
            #            status_code=400,
            #            content={"error": f"Invalid timestamp format: {e}"}
            #        )
            client = self.database.spawn_client()
            dataframe = client.read_measurements(unit, parameter, limit, since_timestamp)
            return dataframe.to_dict(orient="records")

        self.api.include_router(router)
    
    def start(self):
        uvicorn.run(
            self.api,
            host=self.host,
            port=self.port
        )

