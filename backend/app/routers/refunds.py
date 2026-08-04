import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user, get_optional_user, require_role
from app.models.enums import InstallmentStatus, InvestmentStatus, ProjectStatus, UserRole
from app.models.investment import Investment
from app.models.project import Project
from app.models.refund import InvestmentRefundAllocation, RefundInstallment, RefundPlan, RefundTier
from app.models.user import User
from app.schemas.refund import AllocationOut, InstallmentOut, RefundPlanCreate, RefundPlanOut, RefundTierOut
from app.services.knowledge_indexer import reindex_project_knowledge
from app.services.refund_service import (
    estimate_tier_coverage,
    generate_allocations,
    generate_installments,
    validate_tier_chain,
)

router = APIRouter(tags=["Refunds"])

# Le plan de remboursement se définit uniquement pendant que le dossier est
# en brouillon, avant sa soumission pour analyse : il fait partie intégrante
# du dépôt du projet et n'est plus modifiable ensuite (cf. submit_project
# dans projects.py, qui exige qu'un plan existe avant d'accepter la
# soumission — un dossier soumis a donc toujours déjà son plan figé).
PLAN_CREATABLE_STATUSES = {
    ProjectStatus.BROUILLON,
}


@router.post(
    "/projects/{project_id}/refund-plan",
    response_model=RefundPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_refund_plan(
    project_id: uuid.UUID,
    payload: RefundPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le porteur de ce projet")
    if project.status not in PLAN_CREATABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Le plan de remboursement ne peut être défini que pendant que le dossier "
            "est en brouillon, avant sa soumission pour analyse",
        )

    existing = db.query(RefundPlan).filter(RefundPlan.project_id == project_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un plan de remboursement existe déjà pour ce projet")

    tiers = [RefundTier(**tier.model_dump()) for tier in payload.tiers]
    try:
        validate_tier_chain(tiers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    plan = RefundPlan(project_id=project_id, start_date=payload.start_date)
    db.add(plan)
    db.flush()  # récupère plan.id sans committer

    coverage_warnings: list[str] = []
    for tier in tiers:
        tier.refund_plan_id = plan.id
        db.add(tier)
        db.flush()  # récupère tier.id

        total_value, covers_min = estimate_tier_coverage(tier)
        if total_value is not None and not covers_min:
            tier_range = (
                "et plus"
                if tier.tier_max_amount is None
                else f"jusqu'à {tier.tier_max_amount:.0f} MAD"
            )
            coverage_warnings.append(
                f"« {tier.product_description} » ({tier.tier_min_amount:.0f} MAD {tier_range}) : "
                f"valeur estimée {total_value:.0f} MAD, inférieure au minimum du palier."
            )

        installments = generate_installments(db, tier, payload.start_date)
        generate_allocations(db, project_id, tier, installments)

    # Le plan est toujours défini pendant que le dossier est encore en
    # brouillon (cf. PLAN_CREATABLE_STATUSES ci-dessus) : le statut ne change
    # pas ici. C'est la confirmation du dernier investissement qui fera
    # basculer le projet en EN_REMBOURSEMENT une fois entièrement financé
    # (cf. create_investment).
    db.commit()

    plan_out = _load_plan_manually(db, plan.id)
    return RefundPlanOut(
        id=plan_out.id,
        project_id=plan_out.project_id,
        start_date=plan_out.start_date,
        tiers=[RefundTierOut.model_validate(t) for t in plan_out.tiers],
        installments=[InstallmentOut.model_validate(i) for i in plan_out.installments],
        coverage_warnings=coverage_warnings,
    )


@router.get("/projects/{project_id}/refund-plan", response_model=RefundPlanOut)
def get_refund_plan(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Public, comme la fiche projet elle-même (cf. get_project) : les
    contreparties par palier doivent être consultables par un investisseur
    potentiel avant qu'il investisse, pas seulement après.

    L'identité des investisseurs bénéficiaires de chaque échéance (nom,
    contact) n'est en revanche jamais incluse pour un appelant public —
    seul le porteur du projet ou un admin la voit, et seulement une fois le
    projet en remboursement (mêmes règles que project_investments dans
    investments.py)."""
    plan = db.query(RefundPlan).filter(RefundPlan.project_id == project_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Aucun plan de remboursement pour ce projet")

    plan_out = _load_plan_manually(db, plan.id)
    project = db.get(Project, project_id)
    _reveal_installment_beneficiaries(db, plan_out, project, current_user)
    return plan_out


@router.post("/refund-installments/{installment_id}/deliver", response_model=InstallmentOut)
def deliver_installment(
    installment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Le porteur de projet confirme la livraison complète d'une échéance.
    Répercute automatiquement le statut sur chaque allocation investisseur."""
    installment = db.get(RefundInstallment, installment_id)
    if not installment:
        raise HTTPException(status_code=404, detail="Échéance introuvable")

    tier = db.get(RefundTier, installment.refund_tier_id)
    plan = db.get(RefundPlan, tier.refund_plan_id)
    project = db.get(Project, plan.project_id)
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le porteur de ce projet")
    if project.status != ProjectStatus.EN_REMBOURSEMENT:
        raise HTTPException(
            status_code=400,
            detail="Impossible de marquer une échéance livrée avant que le projet ne soit "
            "entièrement financé et passé en remboursement",
        )

    now = datetime.now(timezone.utc)
    installment.quantity_delivered = installment.quantity_due
    installment.status = InstallmentStatus.LIVRE
    installment.delivered_at = now

    allocations = (
        db.query(InvestmentRefundAllocation)
        .filter(InvestmentRefundAllocation.installment_id == installment.id)
        .all()
    )
    for allocation in allocations:
        allocation.status = InstallmentStatus.LIVRE
        allocation.delivered_at = now

    db.commit()

    _maybe_close_project(db, project.id)

    db.refresh(installment)
    return installment


@router.get("/investments/{investment_id}/refund-allocations", response_model=list[AllocationOut])
def my_refund_allocations(
    investment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INVESTISSEUR)),
):
    """Permet à un investisseur de suivre ce qu'il doit recevoir en nature,
    échéance par échéance, pour un investissement donné."""
    investment = db.get(Investment, investment_id)
    if not investment:
        raise HTTPException(status_code=404, detail="Investissement introuvable")
    if investment.investor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cet investissement ne vous appartient pas")

    rows = (
        db.query(InvestmentRefundAllocation, RefundInstallment)
        .join(RefundInstallment, InvestmentRefundAllocation.installment_id == RefundInstallment.id)
        .filter(InvestmentRefundAllocation.investment_id == investment_id)
        .order_by(RefundInstallment.installment_number)
        .all()
    )
    return [
        AllocationOut(
            id=alloc.id,
            investment_id=alloc.investment_id,
            quantity_allocated=alloc.quantity_allocated,
            status=alloc.status,
            delivered_at=alloc.delivered_at,
            installment_number=installment.installment_number,
            due_date=installment.due_date,
        )
        for alloc, installment in rows
    ]


def _load_plan_manually(db: Session, plan_id: uuid.UUID) -> RefundPlan:
    """Les modèles n'ont pas de relations ORM déclarées (choix volontaire pour
    rester explicite) : on recompose la structure imbriquée à la main pour
    la sérialisation Pydantic (RefundPlanOut / RefundTierOut / InstallmentOut)."""
    plan = db.get(RefundPlan, plan_id)
    tiers = (
        db.query(RefundTier)
        .filter(RefundTier.refund_plan_id == plan_id)
        .order_by(RefundTier.tier_min_amount)
        .all()
    )
    all_installments = []
    for tier in tiers:
        installments = (
            db.query(RefundInstallment)
            .filter(RefundInstallment.refund_tier_id == tier.id)
            .order_by(RefundInstallment.installment_number)
            .all()
        )
        for installment in installments:
            installment.allocations = (
                db.query(InvestmentRefundAllocation)
                .filter(InvestmentRefundAllocation.installment_id == installment.id)
                .all()
            )
        all_installments.extend(installments)

    plan.tiers = tiers
    plan.installments = all_installments
    return plan


def _reveal_installment_beneficiaries(
    db: Session, plan: RefundPlan, project: Project, current_user: User | None
) -> None:
    """Attache le nom/contact de l'investisseur sur chaque allocation, pour
    que le porteur sache concrètement à qui livrer à chaque échéance.

    Mêmes conditions que project_investments (investments.py) : réservé au
    porteur ou à un admin, une fois le projet en remboursement, et seulement
    pour les investissements confirmés dont l'investisseur a consenti au
    partage de contact. Par défaut (appelant public, autre statut, pas de
    consentement) les champs investor_* restent à None sur AllocationOut."""
    is_owner = current_user is not None and project.owner_id == current_user.id
    is_admin = current_user is not None and current_user.role == UserRole.ADMIN
    if not (is_owner or is_admin) or project.status != ProjectStatus.EN_REMBOURSEMENT:
        return

    investment_ids = {
        alloc.investment_id for installment in plan.installments for alloc in installment.allocations
    }
    if not investment_ids:
        return

    rows = (
        db.query(Investment, User)
        .join(User, Investment.investor_id == User.id)
        .filter(Investment.id.in_(investment_ids))
        .all()
    )
    investors_by_investment = {
        investment.id: investor
        for investment, investor in rows
        if investment.status == InvestmentStatus.CONFIRME and investment.share_contact_consent
    }

    for installment in plan.installments:
        for alloc in installment.allocations:
            investor = investors_by_investment.get(alloc.investment_id)
            if investor:
                alloc.investor_name = investor.full_name
                alloc.investor_phone = investor.phone
                alloc.investor_city = investor.city
                alloc.investor_region = investor.region


def _maybe_close_project(db: Session, project_id: uuid.UUID) -> None:
    """Passe le projet en CLOS quand toutes les échéances, tous paliers
    confondus, ont été livrées."""
    plan = db.query(RefundPlan).filter(RefundPlan.project_id == project_id).first()
    if not plan:
        return
    tier_ids = [t.id for t in db.query(RefundTier).filter(RefundTier.refund_plan_id == plan.id).all()]
    if not tier_ids:
        return
    remaining = (
        db.query(RefundInstallment)
        .filter(
            RefundInstallment.refund_tier_id.in_(tier_ids),
            RefundInstallment.status != InstallmentStatus.LIVRE,
        )
        .count()
    )
    if remaining == 0:
        project = db.get(Project, project_id)
        project.status = ProjectStatus.CLOS
        project.closed_at = datetime.now(timezone.utc)
        db.commit()

        # CLOS sort le projet de la visibilité publique : réindexation RAG.
        reindex_project_knowledge.delay(str(project_id))
