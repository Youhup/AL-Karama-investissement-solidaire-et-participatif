"""
Extraction de texte des documents uploadés (CIN, devis, attestations...).

Stratégie :
- Image (jpg/png) -> OCR direct avec Tesseract.
- PDF -> on tente d'abord l'extraction de texte natif (rapide, fiable).
  Si le PDF ne contient pas de texte exploitable (cas d'un scan), on
  rasterise les pages en images et on passe chaque page à l'OCR.

Dépendances système requises (à installer sur le serveur, hors du
sandbox de dev) : tesseract-ocr, poppler-utils (pour pdf2image).
"""

import logging
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document

logger = logging.getLogger(__name__)

MIN_NATIVE_TEXT_LENGTH = 30  # en dessous de ce seuil, on considère le PDF "scanné"


def _extract_from_image(file_path: str) -> str:
    image = Image.open(file_path)
    return pytesseract.image_to_string(image, lang="fra+ara")


def _extract_native_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_pdf_via_ocr(file_path: str) -> str:
    pages = convert_from_path(file_path, dpi=200)
    return "\n".join(pytesseract.image_to_string(page, lang="fra+ara") for page in pages)


def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix in (".jpg", ".jpeg", ".png", ".webp"):
        return _extract_from_image(file_path)

    if suffix == ".pdf":
        native_text = _extract_native_pdf_text(file_path)
        if len(native_text.strip()) >= MIN_NATIVE_TEXT_LENGTH:
            return native_text
        logger.info("PDF sans texte natif exploitable, bascule sur l'OCR : %s", file_path)
        return _extract_pdf_via_ocr(file_path)

    logger.warning("Type de fichier non pris en charge pour l'OCR : %s", file_path)
    return ""


@celery_app.task(name="run_document_ocr")
def run_document_ocr(document_id: str):
    """Tâche asynchrone déclenchée après chaque upload de document."""
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if not document:
            return

        try:
            text = extract_text(document.file_path)
        except Exception:
            logger.exception("Échec OCR pour le document %s", document_id)
            text = ""

        document.extracted_text = text
        db.commit()
