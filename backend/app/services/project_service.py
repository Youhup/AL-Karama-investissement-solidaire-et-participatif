from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import ProjectStatus
from app.models.project import Project


def funding_deadline(project: Project) -> datetime | None:
    """Échéance de la collecte : funding_duration_days après validation.
    None tant que le projet n'a pas été validé (le compte à rebours ne
    démarre qu'à ce moment-là, cf. routers/admin.py::decide)."""
    if project.validated_at is None:
        return None
    return project.validated_at + timedelta(days=project.funding_duration_days)


def expire_funding_if_overdue(db: Session, project: Project) -> bool:
    """Clôture une collecte qui n'a pas atteint son objectif avant son
    échéance. Ce MVP n'a pas de tâche planifiée en tâche de fond (pas
    d'infra Celery Beat) : l'expiration se vérifie donc paresseusement à
    chaque lecture ou tentative d'investissement sur le projet (cf.
    routers/projects.py, routers/investments.py::create_investment).

    Ne commit QUE si le statut bascule effectivement — sinon no-op, pour ne
    pas interférer avec une transaction/verrou de ligne en cours chez
    l'appelant (cf. create_investment)."""
    if project.status not in (ProjectStatus.VALIDE, ProjectStatus.EN_FINANCEMENT):
        return False

    deadline = funding_deadline(project)
    if deadline is None or datetime.now(timezone.utc) < deadline:
        return False

    project.status = ProjectStatus.ECHOUE
    project.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return True
