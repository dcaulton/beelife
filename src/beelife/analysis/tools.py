from datetime import date, datetime, timedelta
from statistics import correlation
from typing import Any, Literal

import httpx
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.data_models import (
    CorrelationResult,
    DailyActivitySummary,
    DailyForecast,
    DailyWeatherSummary,
    TrendComparison,
)
from beelife.db.models import Device

# ============================================================
# Core Low-Level Tools
# ============================================================


async def get_daily_weather_data(session: AsyncSession, start_date: date, end_date: date) -> list[DailyWeatherSummary]:
    """Return daily weather aggregates for the given date range."""
    from beelife.db.models import WeatherObservation  # adjust import if needed

    stmt = (
        select(
            func.date(WeatherObservation.timestamp).label("date"),
            func.avg(WeatherObservation.temperature).label("avg_temperature"),
            func.min(WeatherObservation.temperature).label("min_temperature"),
            func.max(WeatherObservation.temperature).label("max_temperature"),
            func.sum(WeatherObservation.precipitation_inches).label("total_precipitation"),
            func.avg(WeatherObservation.wind_speed_mph).label("avg_wind_speed"),
            func.avg(WeatherObservation.relative_humidity).label("avg_humidity"),
        )
        .where(WeatherObservation.timestamp >= start_date)  # type: ignore[arg-type]
        .where(WeatherObservation.timestamp < end_date + timedelta(days=1))  # type: ignore[arg-type]
        .group_by(func.date(WeatherObservation.timestamp))
        .order_by("date")
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        DailyWeatherSummary(
            date=row.date,
            avg_temperature=row.avg_temperature,
            min_temperature=row.min_temperature,
            max_temperature=row.max_temperature,
            total_precipitation=row.total_precipitation,
            avg_wind_speed=row.avg_wind_speed,
            avg_humidity=row.avg_humidity,
        )
        for row in rows
    ]


async def get_daily_bee_activity(session: AsyncSession, start_date: date, end_date: date) -> list[DailyActivitySummary]:
    """Return daily bee activity aggregates (radar + vibration)."""
    from beelife.db.models import BeeDarReading

    stmt = (
        select(
            func.date(BeeDarReading.timestamp).label("date"),
            func.sum(BeeDarReading.radar_activity).label("total_radar_activity"),
            func.avg(BeeDarReading.radar_activity).label("avg_radar_activity"),
            func.avg(BeeDarReading.vibration_level).label("avg_vibration_level"),
            func.count().label("reading_count"),
        )
        .where(BeeDarReading.timestamp >= start_date)  # type: ignore[arg-type]
        .where(BeeDarReading.timestamp < end_date + timedelta(days=1))  # type: ignore[arg-type]
        .group_by(func.date(BeeDarReading.timestamp))
        .order_by("date")
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        DailyActivitySummary(
            date=row.date,
            total_radar_activity=row.total_radar_activity,
            avg_radar_activity=row.avg_radar_activity,
            avg_vibration_level=row.avg_vibration_level,
            reading_count=row.reading_count,
        )
        for row in rows
    ]


async def get_trend_comparison(
    session: AsyncSession,
    baseline_start: date,
    baseline_end: date,
    comparison_start: date,
    comparison_end: date,
    metric: str,
) -> TrendComparison:
    from beelife.db.models import BeeDarReading, WeatherObservation

    model: type[BeeDarReading] | type[WeatherObservation]
    column: Any

    if metric in ("radar_activity", "vibration_level"):
        model = BeeDarReading
        column = getattr(BeeDarReading, metric)
    elif metric == "temperature":
        model = WeatherObservation
        column = WeatherObservation.temperature
    else:
        return TrendComparison(
            metric=metric,
            interpretation=f"Unsupported metric: {metric}",
        )

    def _get_period_avg(model: type, column: Any, start: date, end: date) -> Select[tuple[Any]]:
        return (
            select(func.avg(column))
            .where(model.timestamp >= start)  # type: ignore[attr-defined]
            .where(model.timestamp < end + timedelta(days=1))  # type: ignore[attr-defined]
        )

    baseline_value = (await session.execute(_get_period_avg(model, column, baseline_start, baseline_end))).scalar()
    comparison_value = (
        await session.execute(_get_period_avg(model, column, comparison_start, comparison_end))
    ).scalar()

    if baseline_value and comparison_value:
        percent_change = ((comparison_value - baseline_value) / baseline_value) * 100
        interpretation = (
            f"{metric.replace('_', ' ').title()} changed by {percent_change:.1f}% "
            f"({'increased' if percent_change > 0 else 'decreased'}) compared to baseline."
        )
    else:
        percent_change = None
        interpretation = "Insufficient data for comparison."

    return TrendComparison(
        metric=metric,
        current_period_value=comparison_value,
        previous_period_value=baseline_value,
        percent_change=percent_change,
        interpretation=interpretation,
    )


async def get_activity_weather_correlation(
    session: AsyncSession, start_date: date, end_date: date
) -> CorrelationResult:
    """
    Analyze correlation between daily radar activity and weather variables.
    Currently focuses on wind speed.
    """
    from beelife.db.models import BeeDarReading, WeatherObservation

    # Get daily averages for activity and wind
    activity_stmt = (
        select(
            func.date(BeeDarReading.timestamp).label("date"),
            func.avg(BeeDarReading.radar_activity).label("avg_activity"),
        )
        .where(BeeDarReading.timestamp >= start_date)  # type: ignore[arg-type]
        .where(BeeDarReading.timestamp < end_date + timedelta(days=1))  # type: ignore[arg-type]
        .group_by(func.date(BeeDarReading.timestamp))
    )

    weather_stmt = (
        select(
            func.date(WeatherObservation.timestamp).label("date"),
            func.avg(WeatherObservation.wind_speed_mph).label("avg_wind"),
        )
        .where(WeatherObservation.timestamp >= start_date)  # type: ignore[arg-type]
        .where(WeatherObservation.timestamp < end_date + timedelta(days=1))  # type: ignore[arg-type]
        .group_by(func.date(WeatherObservation.timestamp))
    )

    activity_rows = (await session.execute(activity_stmt)).all()
    weather_rows = (await session.execute(weather_stmt)).all()

    # Join on date
    joined = {}
    for row in activity_rows:
        joined[row.date] = {"activity": row.avg_activity}
    for row in weather_rows:
        if row.date in joined:
            joined[row.date]["wind"] = row.avg_wind

    activities = [v["activity"] for v in joined.values() if "wind" in v]
    winds = [v["wind"] for v in joined.values() if "wind" in v]

    if len(activities) >= 3:
        try:
            corr = correlation(activities, winds)
            strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
            notes = f"Correlation between radar activity and wind speed: {corr:.2f} ({strength})"
        except Exception:
            strength = None
            notes = "Could not calculate correlation."
    else:
        strength = None
        notes = "Not enough overlapping data to calculate correlation."

    if strength in ("weak", "moderate", "strong"):
        correlation_strength: Literal["weak", "moderate", "strong"] | None = strength  # type: ignore[assignment]
    else:
        correlation_strength = None

    return CorrelationResult(
        weather_variable="wind_speed",
        correlation_strength=correlation_strength,
        notes=notes,
    )


async def get_weather_forecast(
    session: AsyncSession, device_id: str | None = None, days: int = 7
) -> list[DailyForecast]:
    """
    Get weather forecast from National Weather Service.

    If device_id is not provided, it will try to use the single active device
    (same behavior as generate_analysis_report).
    """
    from beelife.db.repositories import get_default_device

    # Resolve device_id if not provided
    if device_id is None:
        default_device = await get_default_device(session)
        if default_device is None:
            raise ValueError("No default device available. Please specify device_id.")
        device_id = default_device.device_id

    # Get device location
    stmt = select(Device).where(Device.device_id == device_id)  # type: ignore[arg-type]
    result = await session.execute(stmt)
    device = result.scalar_one_or_none()
    if not device or device.latitude is None or device.longitude is None:
        raise ValueError(f"Device {device_id} does not have latitude/longitude configured.")

    lat = device.latitude
    lon = device.longitude

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Get forecast endpoint from points API
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        points_resp = await client.get(points_url)
        points_resp.raise_for_status()
        points_data = points_resp.json()

        forecast_url = points_data["properties"]["forecast"]

        # Step 2: Get the forecast
        forecast_resp = await client.get(forecast_url)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

        periods = forecast_data["properties"]["periods"]

        forecasts: list[DailyForecast] = []
        for period in periods:
            try:
                forecast_date = datetime.fromisoformat(period["startTime"].replace("Z", "+00:00")).date()

                precip = period.get("probabilityOfPrecipitation", {}).get("value")

                forecasts.append(
                    DailyForecast(
                        date=forecast_date,
                        name=period.get("name"),
                        temperature=period.get("temperature"),
                        temperature_unit=period.get("temperatureUnit"),
                        short_forecast=period.get("shortForecast"),
                        detailed_forecast=period.get("detailedForecast"),
                        wind_speed=period.get("windSpeed"),
                        wind_direction=period.get("windDirection"),
                        precipitation_chance=precip,
                    )
                )
            except Exception:
                continue

        return forecasts[:days]


# ============================================================
# Placeholder Tools (return dummy data for now)
# ============================================================


async def get_long_term_trends(current_start: date, current_end: date, comparison_year: int) -> dict:
    """Placeholder for comparing current period against previous years."""
    return {
        "comparison_year": comparison_year,
        "notes": "Long-term trend analysis not yet implemented.",
        "radar_activity_change": "-12%",
    }
