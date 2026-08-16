import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import DocumentType, pg_enum


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(pg_enum(DocumentType, "document_type"))
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(255))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    # SHA-256 du contenu du fichier, calculé à l'upload (cf. routers/
    # documents.py). Sert à détecter la réutilisation d'un même fichier
    # (CIN, photo, devis...) entre dossiers et entre comptes — signal de
    # fraude fort, cf. agentic_analysis/tools.py. Nullable : les documents
    # antérieurs à cette colonne sont backfillés paresseusement par
    # l'analyse (le conteneur de migration n'a pas accès au volume uploads).
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
