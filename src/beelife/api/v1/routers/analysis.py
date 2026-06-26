from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.report_models import AnalysisReport
from beelife.analysis.reports import generate_analysis_report
from beelife.db.session import get_db

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/daily-report")
async def daily_analysis_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: str | None = None,
) -> AnalysisReport:
    report = await generate_analysis_report(session=db, device_id=device_id)
    return report
