import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.enums import InvestmentStatus, ProjectStatus, UserRole
from app.models.investment import Investment
from app.models.project import Project
from app.models.refund import RefundPlan
from app.models.user import User
from app.schemas.investment import InvestmentCreate, InvestmentOut, ProjectInvestmentOut
from app.services.project_service import expire_funding_if_overdue
from app.services.refund_service import generate_allocations_for_investment

router = APIRouter(tags=["Investments"])

INVESTABLE_STATUSES = {ProjectStatus.VALIDE, ProjectStatus.EN_FINANCEMENT}


@router.post(
    "/projects/{project_id}/investments",
    response_model=InvestmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_investment(
    project_id: uuid.UUID,
    payload: InvestmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INVESTISSEUR)),
):
    # Verrouille la ligne projet le temps de la transaction : évite qu'un
    # deuxième investissement concurrent dépasse le montant demandé
    # (deux requêtes simultanées ne peuvent pas lire le même amount_raised).
    project = (
        db.query(Project).filter(Project.id == project_id).with_for_update().first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    if project.owner_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas investir dans votre propre projet"
        )

    # Bascule le projet en ECHOUE s'il a dépassé sa date limite de collecte
    # sans atteindre son objectif (pas de tâche planifiée dans ce MVP, cf.
    # project_service.expire_funding_if_overdue) — avant de vérifier qu'il
    # est encore investissable, sinon on accepterait un investissement sur
    # une collecte en réalité déjà terminée.
    expire_funding_if_overdue(db, project)
    if project.status not in INVESTABLE_STATUSES:
        raise HTTPException(
            status_code=400, detail="Ce projet n'est pas ouvert au financement actuellement"
        )

    # payload.amount est garanti multiple de 100 MAD par le schéma
    # (InvestmentCreate), tout comme amount_requested (ProjectCreate) : le
    # reliquat à financer (`remaining`) reste donc toujours 0 ou >= 100,
    # jamais coincé sous le minimum d'investissement de la plateforme.
    remaining = float(project.amount_requested) - float(project.amount_raised)
    if payload.amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Montant trop élevé, il reste {remaining:.2f} {project.currency} à financer",
        )

    # NOTE : l'investissement est considéré confirmé immédiatement (MVP).
    # En production, brancher un vrai fournisseur de paiement (ex: CMI,
    # Stripe) et garder status=EN_ATTENTE jusqu'à confirmation par webhook,
    # avant de passer à CONFIRME et de créditer amount_raised.
    investment = Investment(
        project_id=project.id,
        investor_id=current_user.id,
        amount=payload.amount,
        status=InvestmentStatus.CONFIRME,
        share_contact_consent=payload.share_contact_consent,
    )
    db.add(investment)
    db.flush()  # récupère investment.id, nécessaire pour les allocations ci-dessous

    # Si un plan de remboursement a déjà été défini par le porteur (possible
    # dès que le projet est ouvert au financement, pas seulement une fois
    # entièrement financé), on alloue immédiatement ses échéances à ce nouvel
    # investisseur selon le palier correspondant à son montant.
    generate_allocations_for_investment(db, investment)

    project.amount_raised = float(project.amount_raised) + payload.amount
    if project.status == ProjectStatus.VALIDE:
        project.status = ProjectStatus.EN_FINANCEMENT

    if project.amount_raised >= float(project.amount_requested):
        project.status = ProjectStatus.FINANCE
        project.closed_at = datetime.now(timezone.utc)
        # Le plan existait déjà avant la fin du financement : le remboursement
        # peut démarrer immédiatement.
        has_plan = db.query(RefundPlan).filter(RefundPlan.project_id == project.id).first()
        if has_plan:
            project.status = ProjectStatus.EN_REMBOURSEMENT

    db.commit()
    db.refresh(investment)
    return investment


@router.get("/investments/me", response_model=list[InvestmentOut])
def my_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INVESTISSEUR)),
):
    return (
        db.query(Investment)
        .filter(Investment.investor_id == current_user.id)
        .order_by(Investment.invested_at.desc())
        .all()
    )


@router.get("/projects/{project_id}/investments", response_model=list[ProjectInvestmentOut])
def project_investments(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Réservé au porteur du projet (voir qui l'a financé) et aux admins.

    Les coordonnées de l'investisseur (nom, téléphone, ville/région) ne sont
    révélées que si : l'investisseur y a consenti à l'investissement, son
    investissement est confirmé, et le projet est passé en remboursement
    (le porteur n'a besoin de contacter personne avant ce stade — cf.
    discussion produit sur la logistique de livraison en nature)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    is_owner = project.owner_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=403, detail="Accès réservé au porteur du projet ou à un admin"
        )

    rows = (
        db.query(Investment, User)
        .join(User, Investment.investor_id == User.id)
        .filter(Investment.project_id == project_id)
        .order_by(Investment.invested_at.desc())
        .all()
    )

    can_reveal_contacts = project.status == ProjectStatus.EN_REMBOURSEMENT
    results = []
    for investment, investor in rows:
        reveal = (
            can_reveal_contacts
            and investment.status == InvestmentStatus.CONFIRME
            and investment.share_contact_consent
        )
        results.append(
            ProjectInvestmentOut(
                id=investment.id,
                project_id=investment.project_id,
                investor_id=investment.investor_id,
                amount=investment.amount,
                status=investment.status,
                share_contact_consent=investment.share_contact_consent,
                invested_at=investment.invested_at,
                investor_name=investor.full_name if reveal else None,
                investor_phone=investor.phone if reveal else None,
                investor_city=investor.city if reveal else None,
                investor_region=investor.region if reveal else None,
            )
        )
    return results
