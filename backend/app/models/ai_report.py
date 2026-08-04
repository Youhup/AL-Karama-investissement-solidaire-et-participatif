import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import AnalysisVerdict, ProjectStatus, pg_enum


class AIAnalysisReport(Base):
    __tablename__ = "ai_analysis_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    fraud_risk_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    # Nullable : une ligne peut être créée en amont par la décision de
    # l'admin (cf. routers/admin.py) avant que l'analyse IA asynchrone
    # n'ait eu le temps de la compléter.
    verdict: Mapped[AnalysisVerdict | None] = mapped_column(pg_enum(AnalysisVerdict, "analysis_verdict"))
    findings: Mapped[list] = mapped_column(JSONB, default=list)
    raw_model_output: Mapped[dict | None] = mapped_column(JSONB)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    admin_decision: Mapped[ProjectStatus | None] = mapped_column(pg_enum(ProjectStatus, "project_status"))
    admin_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
