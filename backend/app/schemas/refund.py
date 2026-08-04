import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import InstallmentStatus, RepaymentFrequency


class RefundTierCreate(BaseModel):
    tier_min_amount: float = Field(ge=0)
    tier_max_amount: float | None = Field(default=None, ge=0)
    product_description: str
    unit: str
    quantity_per_occurrence: float = Field(gt=0)
    frequency: RepaymentFrequency = RepaymentFrequency.MENSUELLE
    installments_count: int = Field(ge=1, le=60)
    # Facultatif : valeur MAD déclarative servant uniquement à l'avertissement
    # de couverture (jamais une garantie ferme, cf. estimate_tier_coverage).
    estimated_unit_value: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_max_not_below_min(self) -> "RefundTierCreate":
        if self.tier_max_amount is not None and self.tier_max_amount < self.tier_min_amount:
            raise ValueError("tier_max_amount doit être supérieur ou égal à tier_min_amount")
        return self


class RefundPlanCreate(BaseModel):
    start_date: date
    tiers: list[RefundTierCreate] = Field(min_length=1)


class RefundTierOut(BaseModel):
    id: uuid.UUID
    tier_min_amount: float
    tier_max_amount: float | None
    product_description: str
    unit: str
    quantity_per_occurrence: float
    frequency: RepaymentFrequency
    installments_count: int
    estimated_unit_value: float | None

    class Config:
        from_attributes = True


class AllocationOut(BaseModel):
    id: uuid.UUID
    investment_id: uuid.UUID
    quantity_allocated: float
    status: InstallmentStatus
    delivered_at: datetime | None
    # Renseignés uniquement dans le contexte du suivi investisseur
    # (endpoint /investments/{id}/refund-allocations, via jointure sur
    # l'échéance). Lors de la création du plan, les allocations sont
    # sérialisées telles quelles et ces champs restent nuls.
    installment_number: int | None = None
    due_date: date | None = None
    # Identité du bénéficiaire de cette allocation — renseignée uniquement
    # pour le porteur/admin, une fois le projet en remboursement et si
    # l'investisseur a consenti au partage (cf. _reveal_installment_beneficiaries
    # dans refunds.py). None dans tout autre contexte, y compris l'accès public.
    investor_name: str | None = None
    investor_phone: str | None = None
    investor_city: str | None = None
    investor_region: str | None = None

    class Config:
        from_attributes = True


class InstallmentOut(BaseModel):
    id: uuid.UUID
    refund_tier_id: uuid.UUID
    installment_number: int
    due_date: date
    quantity_due: float
    quantity_delivered: float
    status: InstallmentStatus
    delivered_at: datetime | None
    allocations: list[AllocationOut] = []

    class Config:
        from_attributes = True


class RefundPlanOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    start_date: date
    tiers: list[RefundTierOut] = []
    installments: list[InstallmentOut] = []
    # Avertissements non bloquants (ex. palier dont la valeur estimée ne
    # couvre pas le montant minimum investi de la tranche).
    coverage_warnings: list[str] = []

    class Config:
        from_attributes = True
