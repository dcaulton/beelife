from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class WeatherObservation(SQLModel, table=True):
    __tablename__ = "weather_observations"

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), primary_key=True, index=True))

    temperature: float | None = None
    precipitation_inches: float | None = None
    relative_humidity: float | None = None
    cloud_cover: float | None = None
    wind_speed_mph: float | None = None
    surface_pressure_mb: float | None = None
    wind_direction_degrees: float | None = None

    source: str = Field(default="mybroodminder", max_length=50)
    raw_data: dict | None = Field(default=None, sa_column=Column(JSONB().with_variant(JSON, "sqlite")))

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class BeeDarReading(SQLModel, table=True):
    __tablename__ = "beedar_readings"

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), primary_key=True, index=True))

    device_id: str = Field(index=True, max_length=32)
    hive_id: UUID | None = Field(default=None, index=True)

    radar_activity: float | None = None
    vibration_level: float | None = None
    battery_percent: float | None = None

    source: str = Field(default="mybroodminder", max_length=50)
    raw_data: dict | None = Field(default=None, sa_column=Column(JSONB().with_variant(JSON, "sqlite")))
    notes: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


# Useful indexes
Index("ix_beedar_readings_device_time", "device_id", "timestamp")


class Device(SQLModel, table=True):
    __tablename__ = "devices"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: str = Field(unique=True, index=True)  # e.g. "63:02:21"
    name: str | None = None
    type: str = Field(default="beedar")
    hive_position: str | None = None

    # Location (for weather APIs and future use)
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None

    installed_at: datetime | None = None
    notes: str | None = None
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class AnalysisReportRecord(SQLModel, table=True):
    __tablename__ = "analysis_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: str = Field(index=True)

    period_start: date | None = None
    period_end: date | None = None

    status: str = Field(default="pending", index=True)  # pending | completed | failed
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    error_message: str | None = None

    # Full structured report stored as JSONB
    report_data: dict | None = Field(default=None, sa_column=Column(JSONB().with_variant(JSON, "sqlite")))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
