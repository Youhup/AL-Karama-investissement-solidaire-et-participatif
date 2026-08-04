import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import InvestmentStatus, pg_enum


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    investor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[InvestmentStatus] = mapped_column(
        pg_enum(InvestmentStatus, "investment_status"), default=InvestmentStatus.EN_ATTENTE
    )
    # Consentement donné par l'investisseur au moment d'investir : autorise le
    # porteur à voir son nom/téléphone/ville pour organiser la livraison de sa
    # contrepartie en nature. Révocable en théorie (pas encore d'UI pour ça),
    # et de toute façon non exposé au porteur avant EN_REMBOURSEMENT (cf.
    # project_investments dans routers/investments.py).
    share_contact_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
