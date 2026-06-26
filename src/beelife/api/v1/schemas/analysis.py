from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from beelife.analysis.report_models import AnalysisReport


class AnalysisReportListItem(BaseModel):
    """Lightweight response for listing reports (no heavy report_data)."""

    id: UUID
    device_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime


class AnalysisReportDetail(BaseModel):
    """Full report response."""

    id: UUID
    device_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    report: AnalysisReport | None = None  # decoded report when available
