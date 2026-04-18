import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from pandas import DataFrame

from .database import Database

from typing import Dict, Any

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
            limit: int | None = None,
            since_timestamp: str | None = None
        ) -> JSONResponse:
            if since_timestamp != None:

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

