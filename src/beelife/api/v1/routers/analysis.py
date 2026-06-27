from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.graphs import generate_report_graphs
from beelife.analysis.report_models import AnalysisReport
from beelife.analysis.reports import generate_analysis_report
from beelife.api.v1.schemas.analysis import AnalysisReportDetail, AnalysisReportListItem
from beelife.db.models import AnalysisReportRecord
from beelife.db.session import get_db

router = APIRouter(prefix="/analysis", tags=["analysis"])

logger = structlog.get_logger(__name__)


@router.post("/daily-report")
async def daily_analysis_report(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Start a report generation job. Returns immediately with the report_id."""
    record = AnalysisReportRecord(
        device_id=device_id or "unknown",
        status="pending",
        period_start=start_date,
        period_end=end_date,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    background_tasks.add_task(
        _run_analysis_in_background,
        report_id=record.id,
        device_id=device_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    return {"report_id": str(record.id)}


async def _run_analysis_in_background(
    report_id: UUID,
    device_id: str | None,
    start_date: date | None,
    end_date: date | None,
    db: AsyncSession,
) -> None:
    try:
        report = await generate_analysis_report(
            session=db,
            device_id=device_id,
            start_date=start_date,
            end_date=end_date,
            report_id=report_id,
        )

        # Generate graphs after successful report creation
        graphs = generate_report_graphs(report, str(report_id))
        report.graphs = graphs

        record = await db.get(AnalysisReportRecord, report_id)
        if record:
            record.status = "completed"
            record.completed_at = datetime.now(UTC)
            record.period_start = start_date
            record.period_end = end_date
            record.report_data = report.model_dump(mode="json")
            await db.commit()

    except Exception as e:
        record = await db.get(AnalysisReportRecord, report_id)
        if record:
            record.status = "failed"
            record.completed_at = datetime.now(UTC)
            record.error_message = str(e)
            await db.commit()
        logger.exception("analysis_background_task_failed", report_id=str(report_id))


@router.get("/reports")
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
) -> list[AnalysisReportListItem]:
    """List analysis reports (metadata only, no heavy report_data)."""
    stmt = (
        select(AnalysisReportRecord).order_by(AnalysisReportRecord.created_at.desc())  # type: ignore[attr-defined]
    )

    if device_id:
        stmt = stmt.where(AnalysisReportRecord.device_id == device_id)  # type: ignore[arg-type]
    if status:
        stmt = stmt.where(AnalysisReportRecord.status == status)  # type: ignore[arg-type]

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        AnalysisReportListItem(
            id=r.id,
            device_id=r.device_id,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisReportDetail:
    """Get a single report with full decoded report data."""
    record = await db.get(AnalysisReportRecord, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")

    report = None
    if record.report_data:
        try:
            report = AnalysisReport.model_validate(record.report_data)
            graphs = report.graphs
        except Exception:
            report = None
            graphs = None

    return AnalysisReportDetail(
        id=record.id,
        device_id=record.device_id,
        status=record.status,
        started_at=record.started_at,
        completed_at=record.completed_at,
        error_message=record.error_message,
        report=report,
        graphs=graphs,
    )
