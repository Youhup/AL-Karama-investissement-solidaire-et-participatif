import uuid
from datetime import datetime

from sqlalchemy import ARRAY, JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import LegalStatus, ProjectStage, ProjectStatus, pg_enum


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount_requested: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_raised: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="MAD")
    funding_duration_days: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[ProjectStatus] = mapped_column(
        pg_enum(ProjectStatus, "project_status"), default=ProjectStatus.BROUILLON
    )
    city: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))

    # Étape actuelle du projet (dépôt initial)
    project_stage: Mapped[ProjectStage | None] = mapped_column(
        pg_enum(ProjectStage, "project_stage")
    )

    # A. Statut juridique et identité
    legal_status: Mapped[LegalStatus | None] = mapped_column(pg_enum(LegalStatus, "legal_status"))
    legal_id_number: Mapped[str | None] = mapped_column(String(50))
    activity_start_year: Mapped[int | None] = mapped_column(Integer)

    # D. Impact social
    # `with_variant` : reste un vrai ARRAY sur PostgreSQL (production), mais
    # retombe sur JSON en SQLite (utilisé par les tests d'intégration en
    # mémoire, cf. e2e_test.py), qui ne supporte pas nativement ARRAY.
    target_beneficiaries: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(30)).with_variant(JSON(), "sqlite")
    )
    jobs_created: Mapped[int] = mapped_column(Integer, default=0)
    jobs_maintained: Mapped[int] = mapped_column(Integer, default=0)
    social_impact_description: Mapped[str | None] = mapped_column(Text)

    # E. Confiance et historique
    previous_funding: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_funding_details: Mapped[str | None] = mapped_column(Text)
    risk_factors: Mapped[str | None] = mapped_column(Text)

    # F. Présentation
    pitch_summary: Mapped[str | None] = mapped_column(String(140))
    references_text: Mapped[str | None] = mapped_column(Text)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
