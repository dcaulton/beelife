import asyncio
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.report_models import AnalysisReport, BeeStatusReport, WeatherReport
from beelife.db.models import AnalysisReportRecord, Device


@pytest.mark.asyncio
async def test_post_daily_report_creates_pending_record(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """POST /daily-report should create a report record (mocked LLM so it doesn't call real Ollama)."""
    # Create a device so the logic doesn't fail on "no default device"
    device = Device(device_id="63:02:21", name="Test Device")
    async_session.add(device)
    await async_session.commit()

    # Create a fake report that the background task will "generate"
    fake_report = AnalysisReport(
        weather_report=WeatherReport(
            period_start=date(2026, 6, 19),
            period_end=date(2026, 6, 26),
            summary="Test weather",
            trend_notes=[],
            foraging_suitability="good",
        ),
        bee_status=BeeStatusReport(
            period_start=date(2026, 6, 19),
            period_end=date(2026, 6, 26),
            overall_activity_level="moderate",
            activity_trend="stable",
            summary="Test bee status",
        ),
        overall_summary="Test summary",
    )

    with patch(
        "beelife.api.v1.routers.analysis.generate_analysis_report",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = fake_report

        response = await async_client.post("/v1/analysis/daily-report?device_id=63:02:21")

        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data

        report_id = data["report_id"]
        record = await async_session.get(AnalysisReportRecord, report_id)

        assert record is not None
        assert record.device_id == "63:02:21"
        assert record.status in ("pending", "completed")  # status may flip quickly


@pytest.mark.asyncio
async def test_list_reports_returns_metadata_only(async_session: AsyncSession, async_client: AsyncClient) -> None:
    """List endpoint should return metadata without the heavy report_data."""
    # Create a completed report directly in DB
    report = AnalysisReport(
        weather_report=WeatherReport(
            period_start=datetime.now(UTC).date(),
            period_end=datetime.now(UTC).date(),
            summary="Test weather summary",
            trend_notes=[],
            foraging_suitability="good",
        ),
        bee_status=BeeStatusReport(
            period_start=datetime.now(UTC).date(),
            period_end=datetime.now(UTC).date(),
            overall_activity_level="moderate",
            activity_trend="stable",
            summary="Test bee summary",
        ),
        overall_summary="Test overall summary",
    )

    record = AnalysisReportRecord(
        device_id="63:02:21",
        status="completed",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        report_data=report.model_dump(mode="json"),
    )
    async_session.add(record)
    await async_session.commit()

    response = await async_client.get("/v1/analysis/reports")
    assert response.status_code == 200

    data = response.json()
    assert len(data) >= 1
    item = data[0]

    # Should have metadata
    assert "id" in item
    assert item["device_id"] == "63:02:21"
    assert item["status"] == "completed"

    # Should NOT contain the heavy report_data
    assert "report_data" not in item


@pytest.mark.asyncio
async def test_get_report_returns_full_decoded_report(async_session: AsyncSession, async_client: AsyncClient) -> None:
    """Fetching a specific report should return the decoded AnalysisReport."""
    report = AnalysisReport(
        weather_report=WeatherReport(
            period_start=datetime.now(UTC).date(),
            period_end=datetime.now(UTC).date(),
            summary="Nice weather",
            trend_notes=["Getting warmer"],
            foraging_suitability="good",
        ),
        bee_status=BeeStatusReport(
            period_start=datetime.now(UTC).date(),
            period_end=datetime.now(UTC).date(),
            overall_activity_level="high",
            activity_trend="increasing",
            summary="Bees are active",
        ),
        overall_summary="Everything looks good.",
    )

    record = AnalysisReportRecord(
        device_id="63:02:21",
        status="completed",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        report_data=report.model_dump(mode="json"),
    )
    async_session.add(record)
    await async_session.commit()
    await async_session.refresh(record)

    response = await async_client.get(f"/v1/analysis/reports/{record.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(record.id)
    assert data["status"] == "completed"
    assert data["report"] is not None
    assert data["report"]["overall_summary"] == "Everything looks good."
    assert data["report"]["weather_report"]["foraging_suitability"] == "good"


@pytest.mark.asyncio
async def test_post_daily_report_eventually_completes(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """POST should create a pending record, then background task should mark it completed."""
    # Create a device so the report generation doesn't fail on "no default device"
    device = Device(device_id="63:02:21", name="Test Device")
    async_session.add(device)
    await async_session.commit()

    # Create a fake but valid AnalysisReport
    fake_report = AnalysisReport(
        weather_report=WeatherReport(
            period_start=date(2026, 6, 19),
            period_end=date(2026, 6, 26),
            summary="Test weather summary",
            trend_notes=[],
            foraging_suitability="good",
        ),
        bee_status=BeeStatusReport(
            period_start=date(2026, 6, 19),
            period_end=date(2026, 6, 26),
            overall_activity_level="moderate",
            activity_trend="stable",
            summary="Test bee summary",
        ),
        overall_summary="Test overall summary",
    )

    with patch(
        "beelife.api.v1.routers.analysis.generate_analysis_report",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = fake_report

        # Trigger the endpoint
        response = await async_client.post("/v1/analysis/daily-report?device_id=63:02:21")
        assert response.status_code == 200
        report_id = response.json()["report_id"]

        # Give the BackgroundTask a moment to run
        await asyncio.sleep(0.05)

        # Refresh and check the record
        record = await async_session.get(AnalysisReportRecord, report_id)
        assert record is not None
        assert record.status == "completed"
        assert record.report_data is not None
        assert record.completed_at is not None
