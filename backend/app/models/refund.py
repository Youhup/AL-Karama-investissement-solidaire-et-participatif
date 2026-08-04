import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import InstallmentStatus, RepaymentFrequency, pg_enum


class RefundPlan(Base):
    """En-tête du plan de remboursement en nature d'un projet.

    Le détail (produit, quantité, fréquence) vit désormais sur RefundTier :
    un plan peut proposer plusieurs contreparties différentes selon la
    tranche de montant investi (ex. œufs pour les petits montants, poule
    pour les plus gros)."""

    __tablename__ = "refund_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefundTier(Base):
    """Un palier du plan : la contrepartie en nature due à tout investisseur
    dont le montant investi tombe dans [tier_min_amount, tier_max_amount]."""

    __tablename__ = "refund_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    refund_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("refund_plans.id"), nullable=False)
    tier_min_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # None uniquement sur le dernier palier (pas de plafond).
    tier_max_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    product_description: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity_per_occurrence: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    frequency: Mapped[RepaymentFrequency] = mapped_column(
        pg_enum(RepaymentFrequency, "repayment_frequency"), default=RepaymentFrequency.MENSUELLE
    )
    installments_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Valeur MAD déclarative facultative, sert uniquement à l'avertissement
    # de couverture affiché au porteur — jamais une garantie ferme.
    estimated_unit_value: Mapped[float | None] = mapped_column(Numeric(12, 2))


class RefundInstallment(Base):
    __tablename__ = "refund_installments"
    __table_args__ = (UniqueConstraint("refund_tier_id", "installment_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    refund_tier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("refund_tiers.id"), nullable=False)
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_due: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    quantity_delivered: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    status: Mapped[InstallmentStatus] = mapped_column(
        pg_enum(InstallmentStatus, "installment_status"), default=InstallmentStatus.A_VENIR
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InvestmentRefundAllocation(Base):
    __tablename__ = "investment_refund_allocations"
    __table_args__ = (UniqueConstraint("installment_id", "investment_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("refund_installments.id"), nullable=False)
    investment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investments.id"), nullable=False)
    quantity_allocated: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    status: Mapped[InstallmentStatus] = mapped_column(
        pg_enum(InstallmentStatus, "installment_status"), default=InstallmentStatus.A_VENIR
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
