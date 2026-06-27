from datetime import date
from typing import Literal

from pydantic import BaseModel
from sqlmodel import Field


class WeatherReport(BaseModel):
    """Weather trends and short-term forecast summary."""

    period_start: date
    period_end: date
    summary: str = Field(description="Natural language summary of weather conditions and trends")
    trend_notes: list[str] = Field(
        default_factory=list, description="Notable trends (e.g. 'Unusually hot for the past 3 days')"
    )
    foraging_suitability: Literal["poor", "fair", "good", "excellent"]
    forecast_7day_summary: str | None = Field(
        default=None, description="Summary of the upcoming 7-day forecast (placeholder for now)"
    )


class BeeStatusReport(BaseModel):
    """Analysis of bee activity and its relationship to weather."""

    period_start: date
    period_end: date
    overall_activity_level: Literal["low", "moderate", "high"]
    activity_trend: Literal["increasing", "stable", "decreasing"]
    weather_correlation_notes: list[str] = Field(
        default_factory=list, description="How weather appears to be affecting bee activity"
    )
    anomalies: list[str] = Field(default_factory=list, description="Notable anomalies or unusual patterns observed")
    summary: str = Field(description="Concise natural language summary of bee status")


class AnalysisReport(BaseModel):
    """Combined structured output returned to the caller."""

    weather_report: WeatherReport
    bee_status: BeeStatusReport
    overall_summary: str = Field(description="High-level synthesis of weather and bee activity")
    graphs: dict[str, str | None] | None = None
