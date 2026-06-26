import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.report_models import AnalysisReport
from beelife.analysis.reports import generate_analysis_report
from beelife.db.models import BeeDarReading, Device
from beelife.db.repositories import BeeDarRepository, DeviceRepository, get_default_device
from beelife.db.session import get_db

router = APIRouter(prefix="/beedar", tags=["beedar"])

dep_get_db = (Depends(get_db),)


@router.post("/daily-report")
async def daily_analysis_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: str | None = None,
) -> AnalysisReport:
    report = await generate_analysis_report(session=db, device_id=device_id)
    return report


def get_beedar_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> BeeDarRepository:
    return BeeDarRepository(db)


@router.post("/readings/bulk", status_code=201)
async def create_beedar_readings_bulk(
    file: Annotated[UploadFile, File(description="CSV file from MyBroodMinder")],
    repo: Annotated[BeeDarRepository, Depends(get_beedar_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))

    readings = []
    device_ids_seen = set()

    for row in reader:
        device_id = row["Device"]

        # Track unique device_ids in this upload
        device_ids_seen.add(device_id)

        reading = BeeDarReading(
            timestamp=datetime.strptime(row["UTC_TimeStamp"], "%m/%d/%Y %I:%M %p"),
            device_id=device_id,
            radar_activity=float(row["Radar"]) if row.get("Radar") else None,
            vibration_level=float(row["Audio"]) if row.get("Audio") else None,
            battery_percent=float(row["Battery"]) if row.get("Battery") else None,
            source="mybroodminder",
        )
        readings.append(reading)

    # === Auto-create device if it doesn't exist ===
    device_repo = DeviceRepository(db)
    for dev_id in device_ids_seen:
        existing = await device_repo.get(dev_id)
        if not existing:
            new_device = Device(
                device_id=dev_id,
                type="beedar",
                location_name="Darien IL",
                latitude=41.75,
                longitude=-87.98,
            )
            await device_repo.create(new_device)

    # Insert readings
    created = await repo.create_many(readings)
    return {"created": len(created), "filename": file.filename}


@router.get("/readings")
async def list_beedar_readings(
    repo: Annotated[BeeDarRepository, Depends(get_beedar_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: str | None = None,
    start: datetime | None = Query(default=None),  # noqa: B008
    end: datetime | None = Query(default=None),  # noqa: B008
) -> list[BeeDarReading]:
    # Default device logic
    if device_id is None:
        default_device = await get_default_device(db)
        if default_device is None:
            raise HTTPException(status_code=400, detail="Multiple devices found. Please specify device_id.")
        device_id = default_device.device_id

    # Default date range: last 30 days
    now = datetime.now(UTC)
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(days=30)

    return await repo.get_by_device_and_time(device_id, start, end)
