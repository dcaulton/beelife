from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.db.models import BeeDarReading, WeatherObservation


@pytest.mark.asyncio
async def test_create_beedar_reading(async_session: AsyncSession) -> None:
    """Test that we can create and retrieve a BeeDarReading."""
    reading = BeeDarReading(
        timestamp=datetime.now(UTC),
        device_id="63:02:21",
        radar_activity=42.7,
        vibration_level=31.5,
        battery_percent=87.0,
        source="test",
    )

    async_session.add(reading)
    await async_session.commit()
    await async_session.refresh(reading)

    assert reading.id is not None
    assert reading.device_id == "63:02:21"
    assert reading.radar_activity == 42.7


@pytest.mark.asyncio
async def test_create_weather_observation(async_session: AsyncSession) -> None:
    """Test that we can create and retrieve a WeatherObservation."""
    obs = WeatherObservation(
        timestamp=datetime.now(UTC),
        temperature=68.5,
        precipitation_inches=0.12,
        relative_humidity=72.0,
        wind_speed_mph=8.4,
        source="mybroodminder",
    )

    async_session.add(obs)
    await async_session.commit()
    await async_session.refresh(obs)

    assert obs.id is not None
    assert obs.temperature == 68.5
