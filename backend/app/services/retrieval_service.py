"""Recherche sémantique dans la base de connaissances (RAG) pour le chat.

Le scoping par project_id est le garde-fou principal : sans lui, une
recherche purement sémantique pourrait remonter des extraits d'un AUTRE
projet juste parce qu'ils sont sémantiquement proches de la question posée
— ce serait une fuite d'info entre dossiers, pas juste une réponse
imprécise. Quand project_id est fourni, on réserve donc une partie du
budget de résultats (k) aux chunks de ce projet précis, et on complète
avec le contenu global (FAQ/secteurs).

Les projets sont TOUS indexés quel que soit leur statut (cf.
knowledge_indexer.py), pour que le porteur puisse discuter de son propre
dossier même non validé/rejeté. La visibilité se décide donc ici, à la
recherche : un projet au statut non public n'est accessible que si la
conversation appartient à son propriétaire, ou à un admin — cf.
_can_access_project_chunks."""

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ChatRole, KnowledgeSourceType
from app.models.knowledge import KnowledgeChunk
from app.models.project import Project
from app.services.embedding_service import embed
from app.services.knowledge_indexer import PUBLIC_PROJECT_STATUSES


def _can_access_project_chunks(
    db: Session,
    project_id: uuid.UUID,
    context_role: ChatRole,
    requesting_user_id: uuid.UUID | None,
) -> bool:
    project = db.get(Project, project_id)
    if not project:
        return False
    if project.status in PUBLIC_PROJECT_STATUSES:
        return True
    if context_role == ChatRole.ADMIN:
        return True
    return requesting_user_id is not None and requesting_user_id == project.owner_id


def retrieve(
    db: Session,
    query: str,
    context_role: ChatRole,
    project_id: uuid.UUID | None = None,
    requesting_user_id: uuid.UUID | None = None,
    k: int | None = None,
) -> list[KnowledgeChunk]:
    k = k or settings.RAG_TOP_K
    query_vector = embed(query)

    chunks: list[KnowledgeChunk] = []

    if project_id is not None and _can_access_project_chunks(db, project_id, context_role, requesting_user_id):
        chunks = (
            db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.source_type == KnowledgeSourceType.PROJET,
                KnowledgeChunk.source_id == str(project_id),
            )
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(k)
            .all()
        )

    remaining = k - len(chunks)
    if remaining > 0:
        chunks += (
            db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.source_type != KnowledgeSourceType.PROJET,
                (KnowledgeChunk.context_role.is_(None)) | (KnowledgeChunk.context_role == context_role),
            )
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(remaining)
            .all()
        )

    return chunks


def format_context(chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return ""
    return "\n---\n".join(chunk.content for chunk in chunks)
