import hashlib
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.enums import DocumentType, ProjectStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services.ocr_service import run_document_ocr

router = APIRouter(tags=["Documents"])

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_FILE_SIZE_MB = 10


def _check_project_owner(db: Session, project_id: uuid.UUID, current_user: User) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le porteur de ce projet")
    return project


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    project_id: uuid.UUID,
    doc_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project_owner(db, project_id, current_user)
    if project.status != ProjectStatus.BROUILLON:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'ajouter des documents à un dossier déjà soumis",
        )

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Formats acceptés : {', '.join(ALLOWED_EXTENSIONS)}",
        )

    project_dir = Path(settings.UPLOAD_DIR) / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4()}{suffix}"
    file_path = project_dir / stored_filename

    # Copie manuelle par blocs (plutôt que shutil.copyfileobj) pour calculer
    # le SHA-256 au fil de l'écriture : le hash sert à détecter un même
    # fichier réutilisé dans un autre dossier/compte (signal de fraude,
    # cf. agentic_analysis/tools.py::check_duplicate_applications).
    hasher = hashlib.sha256()
    with file_path.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            hasher.update(chunk)
            buffer.write(chunk)

    if file_path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Fichier trop volumineux (max {MAX_FILE_SIZE_MB} Mo)")

    document = Document(
        project_id=project_id,
        doc_type=doc_type,
        file_path=str(file_path),
        original_name=file.filename,
        file_hash=hasher.hexdigest(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # OCR en tâche de fond : le texte extrait alimentera l'IA agentique
    # au moment de la soumission du dossier. Best-effort : un broker Celery
    # injoignable ne doit pas faire échouer un upload déjà enregistré
    # (le document restera simplement sans texte extrait).
    try:
        run_document_ocr.delay(str(document.id))
    except Exception:
        logger.exception("Impossible de planifier l'OCR du document %s", document.id)

    return DocumentOut.from_model(document)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentOut])
def list_documents(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project_owner(db, project_id, current_user)
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    return [DocumentOut.from_model(d) for d in docs]


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable")

    _check_project_owner(db, document.project_id, current_user)

    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le serveur")

    return FileResponse(file_path, filename=document.original_name or file_path.name)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable")

    project = _check_project_owner(db, document.project_id, current_user)
    if project.status != ProjectStatus.BROUILLON:
        raise HTTPException(
            status_code=400, detail="Impossible de supprimer un document d'un dossier déjà soumis"
        )

    Path(document.file_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
