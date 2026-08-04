"""Indexation de la base de connaissances utilisée par le RAG du chat.

Ce qui est indexé, et pourquoi :
- TOUS les projets, quel que soit leur statut (brouillon, soumis, rejeté...)
  — sinon un porteur qui consulte son propre dossier pas encore validé (ou
  rejeté) ne peut pas en parler avec le chat. La visibilité n'est PAS
  gérée à l'indexation mais au moment de la recherche (cf.
  retrieval_service.py::_can_access_project_chunks) : un projet dont le
  statut n'est pas public (cf. PUBLIC_PROJECT_STATUSES ci-dessous, mêmes
  statuts que la liste publique /projects) n'est renvoyé que si la
  conversation appartient au porteur propriétaire, ou à un admin.
- Le cas échéant, la décision de l'admin (validé/rejeté + note explicative)
  est ajoutée au texte indexé du projet — c'est ce qui permet au porteur de
  demander "pourquoi mon dossier a été rejeté ?". Volontairement PAS
  inclus : le score de risque de fraude ni les "findings" de l'IA
  (AIAnalysisReport.fraud_risk_score / findings), qui restent des signaux
  internes réservés à l'admin (même logique que /admin/projects/*/analysis,
  jamais exposés au porteur ailleurs dans l'app).
- Secteurs : contenu public de référence.
- FAQ : contenu pédagogique ESS versionné dans app/data/faq_content.py.
- Documents de référence (textes de loi, définitions officielles...)
  déposés dans app/data/reference_documents/ — cf. le README de ce
  dossier. Contenu public, visible par tous les rôles.

Volontairement PAS indexé : le texte OCR des documents projet (CIN,
relevés bancaires...), ni project.legal_id_number (ICE/RC). Une
conversation de chat peut être ouverte par n'importe quel visiteur
anonyme avec un project_id de son choix (cf. get_optional_user dans
routers/chat.py), et un projet public (cf. PUBLIC_PROJECT_STATUSES) est
alors accessible sans restriction de propriétaire — indexer ces
identifiants risquerait de les exposer à quiconque devine un project_id.
À reconsidérer seulement si le chat gagne un contrôle d'accès par
utilisateur/propriétaire de dossier.

Les montants collectés (amount_raised) ne sont pas non plus inclus dans le
texte indexé : ils changent à chaque investissement, et les embeddings ne
sont de toute façon pas fiables pour restituer des valeurs numériques
exactes. Une question de ce type doit passer par un appel outil sur les
données live plutôt que par le RAG (même logique que agentic_analysis)."""

import logging
from pathlib import Path

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.data.faq_content import FAQ_ENTRIES
from app.db.session import SessionLocal
from app.models.ai_report import AIAnalysisReport
from app.models.enums import ChatRole, KnowledgeSourceType, ProjectStatus
from app.models.knowledge import KnowledgeChunk
from app.models.project import Project
from app.models.project_fund_usage import ProjectFundUsageItem
from app.models.sector import Sector
from app.services.embedding_service import embed_batch
from app.services.ocr_service import extract_text as ocr_extract_text

logger = logging.getLogger(__name__)

PUBLIC_PROJECT_STATUSES = {
    ProjectStatus.VALIDE,
    ProjectStatus.EN_FINANCEMENT,
    ProjectStatus.FINANCE,
}

CHUNK_MAX_CHARS = 800
CHUNK_OVERLAP = 100

REFERENCE_DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "reference_documents"
REFERENCE_TEXT_SUFFIXES = {".txt", ".md"}
REFERENCE_OCR_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def chunk_text(text: str, max_chars: int = CHUNK_MAX_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end - overlap
    return chunks


def _replace_chunks(
    db: Session,
    source_type: KnowledgeSourceType,
    source_id: str,
    texts: list[str],
    context_role: ChatRole | None = None,
) -> None:
    """Supprime les anciens chunks de cette source et les remplace —
    ré-indexation idempotente, pas de gestion de diff fin par fin.

    Le verrou advisory Postgres ci-dessous, scopé par (source_type,
    source_id), sérialise les réindexations concurrentes d'une même
    source (ex : deux tâches reindex_project_knowledge déclenchées à
    quelques secondes d'intervalle pour le même projet — cf. routers/
    projects.py). Sans lui, le DELETE reste non commité pendant tout le
    temps de calcul des embeddings (embed_batch, jusqu'à ~40s le temps
    que le modèle sentence-transformers charge à froid dans un worker
    Celery donné) : une deuxième tâche démarrée dans cette fenêtre ne
    voit ni ne supprime les lignes de la première, et les deux INSERT
    finissent par coexister — doublons dont une version obsolète.
    pg_advisory_xact_lock s'auto-libère au commit/rollback de la
    transaction, pas besoin de déverrouillage explicite."""
    db.execute(
        sql_text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"{source_type.value}:{source_id}"},
    )
    db.query(KnowledgeChunk).filter(
        KnowledgeChunk.source_type == source_type,
        KnowledgeChunk.source_id == source_id,
    ).delete()

    if not texts:
        db.commit()
        return

    vectors = embed_batch(texts)
    for index, (text, vector) in enumerate(zip(texts, vectors)):
        db.add(
            KnowledgeChunk(
                source_type=source_type,
                source_id=source_id,
                chunk_index=index,
                content=text,
                context_role=context_role,
                embedding=vector,
            )
        )
    db.commit()


def index_project(db: Session, project: Project) -> None:
    source_id = str(project.id)

    sector = db.get(Sector, project.sector_id)
    lines = [
        f"Projet : {project.title}",
        f"Statut : {project.status.value}",
        f"Secteur : {sector.name if sector else ''}",
        f"Localisation : {project.city or ''}, {project.region or ''}",
        f"Montant demandé : {project.amount_requested} {project.currency}",
        f"Durée de financement : {project.funding_duration_days} jours",
    ]
    if project.project_stage:
        lines.append(f"Étape du projet : {project.project_stage.value}")
    if project.legal_status:
        lines.append(f"Statut juridique : {project.legal_status.value}")
    if project.activity_start_year:
        lines.append(f"Année de début d'activité : {project.activity_start_year}")
    if project.target_beneficiaries:
        lines.append(f"Bénéficiaires ciblés : {', '.join(project.target_beneficiaries)}")
    lines.append(f"Emplois créés : {project.jobs_created}")
    lines.append(f"Emplois maintenus : {project.jobs_maintained}")
    if project.social_impact_description:
        lines.append(f"Impact social : {project.social_impact_description}")
    lines.append(f"Financement antérieur : {'oui' if project.previous_funding else 'non'}")
    if project.previous_funding_details:
        lines.append(f"Détails du financement antérieur : {project.previous_funding_details}")
    if project.risk_factors:
        lines.append(f"Facteurs de risque déclarés : {project.risk_factors}")
    if project.pitch_summary:
        lines.append(f"Résumé (pitch) : {project.pitch_summary}")
    if project.references_text:
        lines.append(f"Références citées : {project.references_text}")

    fund_usage_items = (
        db.query(ProjectFundUsageItem)
        .filter(ProjectFundUsageItem.project_id == project.id)
        .order_by(ProjectFundUsageItem.created_at)
        .all()
    )
    if fund_usage_items:
        usage_lines = "\n".join(
            f"- {item.category} : {item.amount} {project.currency}"
            + (f" ({item.description})" if item.description else "")
            for item in fund_usage_items
        )
        lines.append(f"Répartition prévue du montant demandé :\n{usage_lines}")

    text = "\n".join(lines) + f"\n\n{project.description}"

    report = (
        db.query(AIAnalysisReport)
        .filter(AIAnalysisReport.project_id == project.id, AIAnalysisReport.admin_decision.isnot(None))
        .order_by(AIAnalysisReport.reviewed_at.desc())
        .first()
    )
    if report:
        text += (
            f"\n\nDécision de l'administrateur : {report.admin_decision.value}\n"
            f"Explication : {report.admin_notes or 'Aucune note laissée par l’administrateur.'}"
        )

    _replace_chunks(db, KnowledgeSourceType.PROJET, source_id, chunk_text(text))


def index_sector(db: Session, sector: Sector) -> None:
    text = f"Secteur : {sector.name}\n{sector.description or ''}"
    _replace_chunks(db, KnowledgeSourceType.SECTEUR, str(sector.id), chunk_text(text))


def index_faq(db: Session) -> None:
    for entry in FAQ_ENTRIES:
        text = f"{entry['title']}\n{entry['content']}"
        _replace_chunks(
            db,
            KnowledgeSourceType.FAQ,
            entry["id"],
            chunk_text(text),
            context_role=entry.get("context_role"),
        )


def _extract_reference_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in REFERENCE_TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8")
    if suffix in REFERENCE_OCR_SUFFIXES:
        return ocr_extract_text(str(path))
    logger.warning("Type de fichier non pris en charge pour l'indexation : %s", path.name)
    return ""


def index_reference_documents(db: Session) -> None:
    """Indexe tout fichier déposé dans app/data/reference_documents/ (voir
    le README de ce dossier pour le workflow d'ajout)."""
    if not REFERENCE_DOCS_DIR.exists():
        return

    indexed_ids = set()
    for path in sorted(REFERENCE_DOCS_DIR.iterdir()):
        if not path.is_file() or path.name == "README.md":
            continue

        source_id = path.name
        indexed_ids.add(source_id)
        try:
            text = _extract_reference_text(path)
        except Exception:
            logger.exception("Échec extraction du document de référence %s", path.name)
            continue

        title = path.stem.replace("-", " ").replace("_", " ")
        _replace_chunks(
            db, KnowledgeSourceType.REFERENCE, source_id, chunk_text(f"{title}\n{text}")
        )

    # Nettoie les chunks des fichiers retirés du dossier depuis la dernière
    # indexation (sinon leur contenu resterait indexé indéfiniment).
    existing_ids = (
        db.query(KnowledgeChunk.source_id)
        .filter(KnowledgeChunk.source_type == KnowledgeSourceType.REFERENCE)
        .distinct()
        .all()
    )
    for (source_id,) in existing_ids:
        if source_id not in indexed_ids:
            _replace_chunks(db, KnowledgeSourceType.REFERENCE, source_id, [])


def reindex_all(db: Session) -> None:
    """Réindexation complète — bootstrap initial ou script manuel."""
    for project in db.query(Project).all():
        index_project(db, project)
    for sector in db.query(Sector).all():
        index_sector(db, sector)
    index_faq(db)
    index_reference_documents(db)


@celery_app.task(name="reindex_project_knowledge")
def reindex_project_knowledge(project_id: str) -> None:
    """Déclenché après toute création/modification d'un projet ou décision
    admin (cf. routers/projects.py, routers/admin.py, routers/refunds.py) —
    le contenu indexé (description, statut, décision admin) doit rester à
    jour pour que le chat puisse en parler avec le porteur propriétaire."""
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if not project:
            _replace_chunks(db, KnowledgeSourceType.PROJET, project_id, [])
            return
        try:
            index_project(db, project)
        except Exception:
            logger.exception("Échec réindexation RAG pour le projet %s", project_id)
