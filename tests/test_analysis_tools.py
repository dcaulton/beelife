from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.tools import (
    get_daily_bee_activity,
    get_daily_weather_data,
    get_weather_forecast,
)
from beelife.db.models import BeeDarReading, Device, WeatherObservation


@pytest.mark.asyncio
async def test_get_daily_weather_data(async_session: AsyncSession) -> None:
    # Seed some weather data
    base = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
    for i in range(3):
        obs = WeatherObservation(
            timestamp=base.replace(day=20 + i),
            temperature=70.0 + i,
            precipitation_inches=0.1 if i == 1 else 0.0,
            wind_speed_mph=5.0,
            relative_humidity=60.0,
            source="test",
        )
        async_session.add(obs)
    await async_session.commit()

    results = await get_daily_weather_data(
        session=async_session,
        start_date=date(2026, 6, 20),
        end_date=date(2026, 6, 22),
    )

    assert len(results) == 3
    assert results[0].avg_temperature == 70.0
    assert results[1].total_precipitation == 0.1


@pytest.mark.asyncio
async def test_get_daily_bee_activity(async_session: AsyncSession) -> None:
    base = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
    for i in range(2):
        reading = BeeDarReading(
            timestamp=base.replace(day=20 + i),
            device_id="63:02:21",
            radar_activity=40.0 + i * 10,
            vibration_level=25.0,
            source="test",
        )
        async_session.add(reading)
    await async_session.commit()

    results = await get_daily_bee_activity(
        session=async_session,
        start_date=date(2026, 6, 20),
        end_date=date(2026, 6, 21),
    )

    assert len(results) == 2
    assert results[0].avg_radar_activity == 40.0
    assert results[1].avg_radar_activity == 50.0


@pytest.mark.asyncio
async def test_get_weather_forecast_mocked(async_session: AsyncSession) -> None:
    # Create a device with location
    device = Device(
        device_id="63:02:21",
        latitude=41.75,
        longitude=-87.98,
        location_name="Darien IL",
    )
    async_session.add(device)
    await async_session.commit()

    # Mock NWS responses
    mock_points_response = MagicMock()
    mock_points_response.json.return_value = {
        "properties": {"forecast": "https://api.weather.gov/gridpoints/TEST/1,2/forecast"}
    }

    mock_forecast_response = MagicMock()
    mock_forecast_response.json.return_value = {
        "properties": {
            "periods": [
                {
                    "startTime": "2026-06-26T00:00:00Z",
                    "name": "This Afternoon",
                    "temperature": 78,
                    "temperatureUnit": "F",
                    "shortForecast": "Sunny",
                    "detailedForecast": "Sunny with light winds.",
                    "windSpeed": "5 mph",
                    "windDirection": "SW",
                    "probabilityOfPrecipitation": {"value": 10},
                }
            ]
        }
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        forecasts = await get_weather_forecast(
            session=async_session,
            device_id="63:02:21",
            days=1,
        )

    assert len(forecasts) == 1
    assert forecasts[0].temperature == 78
    assert forecasts[0].short_forecast == "Sunny"
