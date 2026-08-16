import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_role
from app.models.ai_report import AIAnalysisReport
from app.models.enums import AnalysisVerdict, ProjectStatus, UserRole
from app.models.project import Project
from app.models.user import User
from app.schemas.ai_report import AIAnalysisReportOut
from app.schemas.project import ProjectOut
from app.services.knowledge_indexer import schedule_project_reindex
from app.services.project_service import expire_funding_if_overdue, funding_deadline

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminDecision(BaseModel):
    decision: ProjectStatus  # VALIDE ou REJETE
    notes: str | None = None


@router.get("/projects", response_model=list[ProjectOut])
def list_all_projects(
    status_filter: ProjectStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Vue admin : tous les projets, tous statuts confondus (contrairement
    à la liste publique). Les dossiers en attente de validation (a_valider)
    sont remontés en premier pour prioriser la file de traitement."""
    query = db.query(Project)
    if status_filter:
        query = query.filter(Project.status == status_filter)

    projects = query.order_by(Project.created_at.desc()).all()
    for p in projects:
        expire_funding_if_overdue(db, p)
    priority = {ProjectStatus.A_VALIDER: 0, ProjectStatus.EN_ANALYSE: 1, ProjectStatus.SOUMIS: 2}
    projects.sort(key=lambda p: priority.get(p.status, 99))
    out = []
    for p in projects:
        item = ProjectOut.model_validate(p)
        item.funding_deadline = funding_deadline(p)
        out.append(item)
    return out


@router.get("/projects/{project_id}/analysis", response_model=AIAnalysisReportOut)
def get_analysis(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    report = (
        db.query(AIAnalysisReport)
        .filter(AIAnalysisReport.project_id == project_id)
        .order_by(AIAnalysisReport.analyzed_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Aucune analyse disponible pour ce dossier")
    return report


@router.post("/projects/{project_id}/decision")
def decide(
    project_id: uuid.UUID,
    payload: AdminDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """L'admin tranche APRÈS avoir vu le rapport de l'IA agentique —
    c'est toujours une décision humaine, jamais automatique."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    if payload.decision not in (ProjectStatus.VALIDE, ProjectStatus.REJETE):
        raise HTTPException(
            status_code=400,
            detail="La décision doit être 'valide' ou 'rejete'",
        )

    if project.status != ProjectStatus.A_VALIDER:
        raise HTTPException(
            status_code=409,
            detail=f"Ce projet a déjà été traité (statut actuel : {project.status.value}), "
            "il ne peut pas être validé/rejeté à nouveau",
        )

    report = (
        db.query(AIAnalysisReport)
        .filter(AIAnalysisReport.project_id == project_id)
        .order_by(AIAnalysisReport.analyzed_at.desc())
        .first()
    )
    if report is None:
        # L'admin tranche avant que la tâche Celery d'analyse IA n'ait fini
        # de créer le rapport : on crée quand même une ligne (verdict=None,
        # rempli plus tard par trigger_project_analysis) pour ne pas perdre
        # la décision. Cf. bug où decision/notes disparaissaient sinon.
        report = AIAnalysisReport(project_id=project_id)
        db.add(report)

    report.reviewed_by_admin_id = current_user.id
    report.admin_decision = payload.decision
    report.admin_notes = payload.notes
    report.reviewed_at = datetime.now(timezone.utc)

    project.status = payload.decision
    if payload.decision == ProjectStatus.VALIDE:
        project.validated_at = datetime.now(timezone.utc)

    db.commit()

    # Le dossier peut entrer ou sortir de la visibilité publique (VALIDE vs
    # REJETE) : on réindexe pour le RAG du chat (cf. knowledge_indexer.py).
    schedule_project_reindex(project.id)

    return {"status": "ok", "new_status": project.status}


# Concordance verdict IA <-> décision admin. a_examiner est neutre par
# construction (l'IA demande explicitement l'arbitrage humain) : il ne
# compte ni comme accord ni comme désaccord.
_AGREEMENT_PAIRS = {
    (AnalysisVerdict.RECOMMANDE, ProjectStatus.VALIDE),
    (AnalysisVerdict.SUSPECT, ProjectStatus.REJETE),
    (AnalysisVerdict.REJETE_SUGGERE, ProjectStatus.REJETE),
}
_DISAGREEMENT_PAIRS = {
    (AnalysisVerdict.RECOMMANDE, ProjectStatus.REJETE),
    (AnalysisVerdict.SUSPECT, ProjectStatus.VALIDE),
    (AnalysisVerdict.REJETE_SUGGERE, ProjectStatus.VALIDE),
}


@router.get("/analysis-quality")
def analysis_quality(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Mesure l'accord entre les verdicts de l'IA et les décisions finales
    des admins — chaque rapport tranché est une donnée étiquetée gratuite.
    Le taux de concordance et surtout la liste des désaccords récents
    servent à recalibrer le barème de l'agent (cf. SYSTEM_PROMPT de
    agentic_analysis/agent.py) : c'est la boucle de feedback qualité."""
    rows = (
        db.query(AIAnalysisReport, Project)
        .join(Project, AIAnalysisReport.project_id == Project.id)
        .filter(
            AIAnalysisReport.admin_decision.isnot(None),
            AIAnalysisReport.verdict.isnot(None),
        )
        .order_by(AIAnalysisReport.reviewed_at.desc())
        .all()
    )

    agreements = disagreements = neutral = 0
    matrix: dict[str, dict[str, int]] = {}
    recent_disagreements = []
    for report, project in rows:
        pair = (report.verdict, report.admin_decision)
        verdict_key = report.verdict.value
        decision_key = report.admin_decision.value
        matrix.setdefault(verdict_key, {}).setdefault(decision_key, 0)
        matrix[verdict_key][decision_key] += 1

        if pair in _AGREEMENT_PAIRS:
            agreements += 1
        elif pair in _DISAGREEMENT_PAIRS:
            disagreements += 1
            if len(recent_disagreements) < 10:
                recent_disagreements.append(
                    {
                        "project_id": str(project.id),
                        "project_title": project.title,
                        "ai_verdict": verdict_key,
                        "admin_decision": decision_key,
                        "relevance_score": report.relevance_score,
                        "fraud_risk_score": report.fraud_risk_score,
                        "reviewed_at": report.reviewed_at,
                    }
                )
        else:
            neutral += 1

    conclusive = agreements + disagreements
    return {
        "decided_reports": len(rows),
        "agreements": agreements,
        "disagreements": disagreements,
        "neutral_a_examiner": neutral,
        "agreement_rate_percent": round(agreements / conclusive * 100, 1) if conclusive else None,
        "matrix": matrix,
        "recent_disagreements": recent_disagreements,
    }


# TODO (même pattern que ci-dessus) :
# GET  /admin/users                 -> lister/gérer les utilisateurs
# GET  /admin/projects/suspects      -> filtrer les dossiers à fraud_risk_score élevé
