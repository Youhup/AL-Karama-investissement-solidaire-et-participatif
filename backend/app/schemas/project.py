import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import LegalStatus, ProjectStage, ProjectStatus

# Doit rester un multiple du montant minimum d'investissement de la
# plateforme (cf. PLATFORM_MIN_INVESTMENT dans refund_service.py) : sinon le
# reliquat à financer peut tomber sous ce minimum et devenir impossible à
# investir, bloquant le projet juste avant son objectif.
AMOUNT_STEP = 100


def _check_multiple_of_step(value: float) -> float:
    if round(value) != value or round(value) % AMOUNT_STEP != 0:
        raise ValueError(f"Le montant doit être un multiple de {AMOUNT_STEP} MAD")
    return value


class ProjectCreate(BaseModel):
    title: str
    description: str
    sector_id: int
    amount_requested: float = Field(gt=0)
    funding_duration_days: int = Field(default=60, ge=7)
    city: str | None = None
    region: str | None = None
    project_stage: ProjectStage | None = None

    @field_validator("amount_requested")
    @classmethod
    def check_amount_requested_step(cls, value: float) -> float:
        return _check_multiple_of_step(value)


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    amount_requested: float | None = Field(default=None, gt=0)
    city: str | None = None
    region: str | None = None
    project_stage: ProjectStage | None = None

    @field_validator("amount_requested")
    @classmethod
    def check_amount_requested_step(cls, value: float | None) -> float | None:
        return _check_multiple_of_step(value) if value is not None else None

    # A. Statut juridique et identité
    legal_status: LegalStatus | None = None
    legal_id_number: str | None = None
    activity_start_year: int | None = Field(default=None, ge=1900)

    # D. Impact social
    target_beneficiaries: list[str] | None = None
    jobs_created: int | None = Field(default=None, ge=0)
    jobs_maintained: int | None = Field(default=None, ge=0)
    social_impact_description: str | None = None

    # E. Confiance et historique
    previous_funding: bool | None = None
    previous_funding_details: str | None = None
    risk_factors: str | None = None

    # F. Présentation
    pitch_summary: str | None = Field(default=None, max_length=140)
    references_text: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    sector_id: int
    title: str
    description: str
    amount_requested: float
    amount_raised: float
    status: ProjectStatus
    city: str | None
    region: str | None
    created_at: datetime
    photo_url: str | None = None

    funding_duration_days: int = 60
    # Calculé (validated_at + funding_duration_days) : None tant que le
    # projet n'a pas été validé, cf. services/project_service.py.
    funding_deadline: datetime | None = None

    project_stage: ProjectStage | None = None
    legal_status: LegalStatus | None = None
    legal_id_number: str | None = None
    activity_start_year: int | None = None

    target_beneficiaries: list[str] | None = None
    jobs_created: int = 0
    jobs_maintained: int = 0
    social_impact_description: str | None = None

    previous_funding: bool = False
    previous_funding_details: str | None = None
    risk_factors: str | None = None

    pitch_summary: str | None = None
    references_text: str | None = None

    class Config:
        from_attributes = True


class FundUsageItemCreate(BaseModel):
    category: str
    amount: float = Field(gt=0)
    description: str | None = None


class FundUsageItemOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    category: str
    amount: float
    description: str | None

    class Config:
        from_attributes = True
