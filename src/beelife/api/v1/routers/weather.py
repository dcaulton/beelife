import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import WeatherObservation
from beelife.db.repositories import WeatherRepository
from beelife.db.session import get_db

router = APIRouter(prefix="/weather", tags=["weather"])


def get_weather_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> WeatherRepository:
    return WeatherRepository(db)


@router.post("/bulk", status_code=201)
async def create_weather_bulk(
    file: Annotated[UploadFile, File(description="Weather CSV exported from MyBroodMinder")],
    repo: Annotated[WeatherRepository, Depends(get_weather_repo)],
) -> dict:
    """Upload a weather CSV file exported from MyBroodMinder."""
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))

    observations = []
    for row in reader:
        obs = WeatherObservation(
            timestamp=datetime.strptime(row["UTC_TimeStamp"], "%m/%d/%Y %I:%M %p"),
            temperature=float(row["Temperature"]) if row.get("Temperature") else None,
            precipitation_inches=float(row["Precipitation_inches"]) if row.get("Precipitation_inches") else None,
            relative_humidity=float(row["Relative_Humidity"]) if row.get("Relative_Humidity") else None,
            cloud_cover=float(row["Cloud_Cover"]) if row.get("Cloud_Cover") else None,
            wind_speed_mph=float(row["WindSpeed10mAbove_mph"]) if row.get("WindSpeed10mAbove_mph") else None,
            surface_pressure_mb=(
                float(row["SurfacePressure_millibars"]) if row.get("SurfacePressure_millibars") else None
            ),
            wind_direction_degrees=float(row["WindDirection_degrees"]) if row.get("WindDirection_degrees") else None,
            source="mybroodminder",
        )
        observations.append(obs)

    created = await repo.create_many(observations)
    return {"created": len(created), "filename": file.filename}


@router.get("/")
async def list_weather(
    repo: Annotated[WeatherRepository, Depends(get_weather_repo)],
    start: datetime = Query(),  # noqa: B008
    end: datetime = Query(),  # noqa: B008
) -> list[WeatherObservation]:
    return await repo.get_by_time_range(start, end)
