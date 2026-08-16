import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.document import Document
from app.models.enums import DocumentType, ProjectStatus, UserRole
from app.models.project import Project
from app.models.project_fund_usage import ProjectFundUsageItem
from app.models.refund import RefundPlan
from app.models.user import User
from app.schemas.project import (
    FundUsageItemCreate,
    FundUsageItemOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.services.agentic_analysis.agent import trigger_project_analysis
from app.services.knowledge_indexer import schedule_project_reindex
from app.services.project_service import expire_funding_if_overdue, funding_deadline

router = APIRouter(prefix="/projects", tags=["Projects"])

# Seul le document "photo_projet" sert d'image publique sur les cartes et la
# page projet — les autres types (CIN, relevé bancaire...) restent privés
# (voir routers/documents.py). On ignore un "photo_projet" au format PDF :
# rien ne l'interdit à l'upload, mais ça ne s'affiche pas comme une image.
PHOTO_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _latest_photo_by_project(db: Session, project_ids: list[uuid.UUID]) -> dict[uuid.UUID, Document]:
    if not project_ids:
        return {}
    docs = (
        db.query(Document)
        .filter(Document.project_id.in_(project_ids), Document.doc_type == DocumentType.PHOTO_PROJET)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    latest = {}
    for doc in docs:
        if doc.project_id in latest:
            continue
        if Path(doc.file_path).suffix.lower() not in PHOTO_IMAGE_EXTENSIONS:
            continue
        latest[doc.project_id] = doc
    return latest


def _to_project_out(project: Project, photo: Document | None) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    if photo:
        out.photo_url = f"/projects/{project.id}/photo"
    out.funding_deadline = funding_deadline(project)
    return out


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_role(UserRole.PORTEUR)),
    db: Session = Depends(get_db),
):
    project = Project(owner_id=current_user.id, **payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)

    # Indexé dès la création pour que le porteur puisse en discuter avec le
    # chat même en brouillon (accès réservé au propriétaire, cf.
    # retrieval_service.py).
    schedule_project_reindex(project.id)

    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    sector_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Liste publique : uniquement les projets ouverts au financement ou
    déjà financés. Jamais de brouillon ni de dossier en cours d'analyse,
    quel que soit l'appelant — voir /projects/mine pour ses propres
    dossiers à tous les stades."""
    query = db.query(Project).filter(
        Project.status.in_(
            [ProjectStatus.VALIDE, ProjectStatus.EN_FINANCEMENT, ProjectStatus.FINANCE]
        )
    )
    if sector_id:
        query = query.filter(Project.sector_id == sector_id)

    projects = query.order_by(Project.created_at.desc()).all()
    projects = [p for p in projects if not expire_funding_if_overdue(db, p)]
    photos = _latest_photo_by_project(db, [p.id for p in projects])
    return [_to_project_out(p, photos.get(p.id)) for p in projects]


@router.get("/mine", response_model=list[ProjectOut])
def list_my_projects(
    current_user: User = Depends(require_role(UserRole.PORTEUR)),
    db: Session = Depends(get_db),
):
    """Les projets du porteur connecté, à tous les stades (brouillon,
    en analyse, rejeté...) — utilisé par le tableau de bord porteur.
    Placé avant /{project_id} pour que "mine" ne soit jamais interprété
    comme un UUID de projet."""
    projects = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    for p in projects:
        expire_funding_if_overdue(db, p)
    photos = _latest_photo_by_project(db, [p.id for p in projects])
    return [_to_project_out(p, photos.get(p.id)) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    expire_funding_if_overdue(db, project)
    photo = _latest_photo_by_project(db, [project.id]).get(project.id)
    return _to_project_out(project, photo)


@router.get("/{project_id}/photo")
def get_project_photo(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Sert la photo publique du projet (document de type "photo_projet").
    Public et sans authentification, contrairement à /projects/{id}/documents :
    seule cette image est destinée à être montrée sur les cartes et la page
    projet, jamais les autres pièces du dossier."""
    photo = _latest_photo_by_project(db, [project_id]).get(project_id)
    if not photo or not Path(photo.file_path).exists():
        raise HTTPException(status_code=404, detail="Aucune photo pour ce projet")
    return FileResponse(photo.file_path)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le porteur de ce projet")
    if project.status != ProjectStatus.BROUILLON:
        raise HTTPException(
            status_code=400, detail="Impossible de modifier un dossier déjà soumis"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)

    schedule_project_reindex(project.id)

    return project


@router.post("/{project_id}/submit", response_model=ProjectOut)
def submit_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soumet le dossier : passe en 'soumis' puis déclenche l'analyse
    de l'IA agentique de façon asynchrone (tâche Celery)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le porteur de ce projet")
    if project.status != ProjectStatus.BROUILLON:
        raise HTTPException(status_code=400, detail="Ce dossier a déjà été soumis")

    has_refund_plan = db.query(RefundPlan).filter(RefundPlan.project_id == project_id).first()
    if not has_refund_plan:
        raise HTTPException(
            status_code=400,
            detail="Définissez votre plan de remboursement en nature avant de soumettre le dossier "
            "— il ne sera plus possible d'en ajouter un après la soumission",
        )

    project.status = ProjectStatus.SOUMIS
    project.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    # Lance l'analyse en tâche de fond (voir services/agentic_analysis/agent.py).
    # Si le broker Celery est injoignable, on REVIENT en brouillon plutôt que
    # de laisser un dossier « soumis » qu'aucune analyse ne traitera jamais
    # (soumis n'est pas re-soumissible, et l'admin ne peut trancher qu'un
    # dossier arrivé en a_valider) : le porteur peut simplement réessayer.
    try:
        trigger_project_analysis.delay(str(project.id))
    except Exception:
        project.status = ProjectStatus.BROUILLON
        project.submitted_at = None
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Le service d'analyse est momentanément indisponible, "
            "veuillez soumettre à nouveau dans quelques instants",
        )
    schedule_project_reindex(project.id)

    return project


def _check_project_owner(db: Session, project_id: uuid.UUID, current_user: User) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le porteur de ce projet")
    return project


@router.post(
    "/{project_id}/fund-usage-items",
    response_model=FundUsageItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_fund_usage_item(
    project_id: uuid.UUID,
    payload: FundUsageItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Section B du dossier : un poste de la répartition du montant demandé."""
    project = _check_project_owner(db, project_id, current_user)
    if project.status != ProjectStatus.BROUILLON:
        raise HTTPException(
            status_code=400,
            detail="Impossible de modifier l'utilisation des fonds d'un dossier déjà soumis",
        )

    item = ProjectFundUsageItem(project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    schedule_project_reindex(project_id)
    return item


@router.get("/{project_id}/fund-usage-items", response_model=list[FundUsageItemOut])
def list_fund_usage_items(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Public, comme la fiche projet elle-même (cf. get_project) : un
    investisseur potentiel doit pouvoir voir comment son argent sera utilisé
    avant d'investir. Seules la création et la suppression restent réservées
    au porteur/admin."""
    return (
        db.query(ProjectFundUsageItem)
        .filter(ProjectFundUsageItem.project_id == project_id)
        .order_by(ProjectFundUsageItem.created_at)
        .all()
    )


@router.delete("/fund-usage-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fund_usage_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(ProjectFundUsageItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Poste introuvable")

    project = _check_project_owner(db, item.project_id, current_user)
    if project.status != ProjectStatus.BROUILLON:
        raise HTTPException(
            status_code=400,
            detail="Impossible de modifier l'utilisation des fonds d'un dossier déjà soumis",
        )

    db.delete(item)
    db.commit()
    schedule_project_reindex(project.id)
