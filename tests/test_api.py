import csv
import io
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


def _make_beedar_csv() -> bytes:
    """Create a small valid BeeDar CSV in memory."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "App",
            "Rssi",
            "Device",
            "Hive_Position",
            "Record_Type",
            "UTC_TimeStamp",
            "Local_TimeStamp",
            "Unix_Time",
            "Sample",
            "Metric",
            "Battery",
            "Temperature",
            "Humidity",
            "Radar",
            "Audio",
        ],
    )
    writer.writeheader()

    now = datetime.now(UTC)
    # Format matching what MyBroodMinder exports use
    ts = now.strftime("%m/%d/%Y %I:%M %p")

    writer.writerow(
        {
            "App": "BAPP",
            "Rssi": "0",
            "Device": "63:02:21",
            "Hive_Position": "Lower Brood",
            "Record_Type": "Logged_Data",
            "UTC_TimeStamp": ts,
            "Local_TimeStamp": ts,
            "Unix_Time": "0",
            "Sample": "1",
            "Metric": "false",
            "Battery": "100",
            "Temperature": "65.0",
            "Humidity": "55",
            "Radar": "42.5",
            "Audio": "31.2",
        }
    )

    return output.getvalue().encode("utf-8")


def _make_weather_csv() -> bytes:
    """Create a small valid weather CSV in memory."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "DownloadTimeStamp",
            "UTC_TimeStamp",
            "Local_TimeStamp",
            "Unix_Time",
            "Metric",
            "Temperature",
            "Precipitation_inches",
            "Relative_Humidity",
            "Cloud_Cover",
            "WindSpeed10mAbove_mph",
            "SurfacePressure_millibars",
            "WindDirection_degrees",
        ],
    )
    writer.writeheader()

    now = datetime.now(UTC)
    ts = now.strftime("%m/%d/%Y %I:%M %p")

    writer.writerow(
        {
            "DownloadTimeStamp": "0",
            "UTC_TimeStamp": ts,
            "Local_TimeStamp": ts,
            "Unix_Time": "0",
            "Metric": "false",
            "Temperature": "68.5",
            "Precipitation_inches": "0.12",
            "Relative_Humidity": "72.0",
            "Cloud_Cover": "50",
            "WindSpeed10mAbove_mph": "8.4",
            "SurfacePressure_millibars": "1012",
            "WindDirection_degrees": "180",
        }
    )

    return output.getvalue().encode("utf-8")


@pytest.mark.asyncio
async def test_bulk_create_beedar_readings_from_csv(async_client: AsyncClient) -> None:
    csv_bytes = _make_beedar_csv()
    files = {"file": ("test_beedar.csv", csv_bytes, "text/csv")}

    response = await async_client.post("/v1/beedar/readings/bulk", files=files)
    assert response.status_code == 201
    assert response.json()["created"] == 1


@pytest.mark.asyncio
async def test_bulk_create_weather_from_csv(async_client: AsyncClient) -> None:
    csv_bytes = _make_weather_csv()
    files = {"file": ("test_weather.csv", csv_bytes, "text/csv")}

    response = await async_client.post("/v1/weather/bulk", files=files)
    assert response.status_code == 201
    assert response.json()["created"] == 1
