import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import BeeDarReading
from beelife.db.repositories import BeeDarRepository
from beelife.db.session import get_db

router = APIRouter(prefix="/beedar", tags=["beedar"])


def get_beedar_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> BeeDarRepository:
    return BeeDarRepository(db)


@router.post("/readings/bulk", status_code=201)
async def create_beedar_readings_bulk(
    file: Annotated[UploadFile, File(description="CSV file from MyBroodMinder")],
    repo: Annotated[BeeDarRepository, Depends(get_beedar_repo)],
) -> dict:
    """Upload a CSV file exported from MyBroodMinder (BeeDar readings)."""
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))

    readings = []
    for row in reader:
        # Map CSV columns to our model fields
        reading = BeeDarReading(
            timestamp=datetime.strptime(row["UTC_TimeStamp"], "%m/%d/%Y %I:%M %p"),
            device_id=row["Device"],
            radar_activity=float(row["Radar"]) if row.get("Radar") else None,
            vibration_level=float(row["Audio"]) if row.get("Audio") else None,
            battery_percent=float(row["Battery"]) if row.get("Battery") else None,
            source="mybroodminder",
        )
        readings.append(reading)

    created = await repo.create_many(readings)
    return {"created": len(created), "filename": file.filename}


@router.get("/readings")
async def list_beedar_readings(
    device_id: str,
    repo: Annotated[BeeDarRepository, Depends(get_beedar_repo)],
    start: datetime = Query(),  # noqa: B008
    end: datetime = Query(),  # noqa: B008
) -> list[BeeDarReading]:
    return await repo.get_by_device_and_time(device_id, start, end)
