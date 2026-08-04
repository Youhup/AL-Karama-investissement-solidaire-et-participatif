import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import InvestmentStatus
from app.schemas.project import _check_multiple_of_step


class InvestmentCreate(BaseModel):
    amount: float = Field(gt=0)
    # Consentement explicite pour partager nom/téléphone/ville avec le
    # porteur du projet, uniquement pour organiser la livraison de la
    # contrepartie en nature. Facultatif : investir reste possible sans.
    share_contact_consent: bool = False

    @field_validator("amount")
    @classmethod
    def check_amount_step(cls, value: float) -> float:
        return _check_multiple_of_step(value)


class InvestmentOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    investor_id: uuid.UUID
    amount: float
    status: InvestmentStatus
    share_contact_consent: bool
    invested_at: datetime

    class Config:
        from_attributes = True


class ProjectInvestmentOut(InvestmentOut):
    """Vue porteur/admin de la liste des investissements d'un projet : ajoute
    les coordonnées de l'investisseur quand elles peuvent être révélées (cf.
    routers/investments.py::project_investments pour les conditions)."""

    investor_name: str | None = None
    investor_phone: str | None = None
    investor_city: str | None = None
    investor_region: str | None = None
