import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import ChatRole, KnowledgeSourceType, pg_enum

# Dimension du modèle d'embeddings configuré (EMBEDDING_MODEL) — les deux
# doivent rester alignés, cf. app/services/embedding_service.py.
EMBEDDING_DIM = 384


class KnowledgeChunk(Base):
    """Un fragment de contenu indexé pour la recherche sémantique (RAG) du
    chat : description de projet, secteur, ou entrée de FAQ. `source_id`
    référence l'enregistrement d'origine (UUID de projet, id de secteur,
    slug de FAQ) sans FK — les sources sont de nature différente."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[KnowledgeSourceType] = mapped_column(
        pg_enum(KnowledgeSourceType, "knowledge_source_type")
    )
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Restreint une entrée de FAQ à un rôle (porteur/investisseur/...) ;
    # NULL = visible pour tous les rôles. Sans effet sur les chunks projet,
    # qui sont scopés par project_id (cf. retrieval_service.py).
    context_role: Mapped[ChatRole | None] = mapped_column(pg_enum(ChatRole, "chat_role"), nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
