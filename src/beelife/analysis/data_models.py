from datetime import date
from typing import Literal

from pydantic import BaseModel


class DailyWeatherSummary(BaseModel):
    """Daily weather aggregates for a single day."""

    date: date
    avg_temperature: float | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    total_precipitation: float | None = None
    avg_wind_speed: float | None = None
    avg_humidity: float | None = None
    avg_cloud_cover: float | None = None


class DailyActivitySummary(BaseModel):
    """Daily bee activity aggregates (radar + vibration)."""

    date: date
    total_radar_activity: float | None = None
    avg_radar_activity: float | None = None
    avg_vibration_level: float | None = None
    reading_count: int


class TrendComparison(BaseModel):
    """Comparison between two periods."""

    metric: str
    current_period_value: float | None = None
    previous_period_value: float | None = None
    percent_change: float | None = None
    interpretation: str | None = None


class CorrelationResult(BaseModel):
    """Basic correlation between bee activity and weather."""

    weather_variable: str
    correlation_strength: Literal["weak", "moderate", "strong"] | None = None
    notes: str | None = None


class DateRange(BaseModel):
    """Input schema for tools that accept a start and end date."""

    start_date: date
    end_date: date


class DailyForecast(BaseModel):
    """Structured daily forecast from National Weather Service."""

    date: date
    name: str | None = None  # e.g. "This Afternoon", "Tonight"
    temperature: int | None = None
    temperature_unit: str | None = None  # "F" or "C"
    short_forecast: str | None = None
    detailed_forecast: str | None = None
    wind_speed: str | None = None
    wind_direction: str | None = None
    precipitation_chance: int | None = None  # percentage


class WeatherForecastInput(BaseModel):
    """Input for the weather forecast tool."""

    device_id: str | None = None
    days: int = 7
