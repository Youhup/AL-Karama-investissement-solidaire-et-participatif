import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DocumentType


class DocumentOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    doc_type: DocumentType
    original_name: str | None
    uploaded_at: datetime
    has_extracted_text: bool = False

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, doc):
        return cls(
            id=doc.id,
            project_id=doc.project_id,
            doc_type=doc.doc_type,
            original_name=doc.original_name,
            uploaded_at=doc.uploaded_at,
            has_extracted_text=bool(doc.extracted_text),
        )
