import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AnalysisVerdict, ProjectStatus


class AIAnalysisReportOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    relevance_score: float | None
    fraud_risk_score: float | None
    verdict: AnalysisVerdict | None
    findings: list
    analyzed_at: datetime
    reviewed_by_admin_id: uuid.UUID | None
    admin_decision: ProjectStatus | None
    admin_notes: str | None
    reviewed_at: datetime | None

    class Config:
        from_attributes = True
