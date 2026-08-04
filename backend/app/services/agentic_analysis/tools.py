"""
Chaque fonction ici est un "tool" que le LLM peut appeler via function calling.
Le JSON schema (TOOLS_SCHEMA) est ce qu'on envoie à Groq ; les fonctions Python
sont exécutées côté serveur quand le modèle décide de les appeler.
"""

from statistics import median

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.enums import DocumentType, LegalStatus, ProjectStatus
from app.models.investment import Investment
from app.models.project import Project
from app.models.user import User

# En dessous de ce nombre de projets validés comparables dans le secteur,
# une comparaison statistique n'est pas fiable (trop peu de données) :
# check_sector_benchmark le signale au lieu de calculer un ratio bruité.
MIN_COMPARABLE_PROJECTS = 5

# Pièces attendues selon le statut juridique déclaré, en plus du CIN
# (toujours requis : identité du porteur). Repose sur les types de
# justificatif officiel propres à chaque statut (registre de commerce
# pour les entités commerciales, attestation/récépissé pour les autres) —
# à ajuster si la réalité administrative marocaine diverge de cette
# hypothèse simplifiée.
REQUIRED_DOCS_BY_LEGAL_STATUS: dict[LegalStatus, set[DocumentType]] = {
    LegalStatus.SARL: {DocumentType.REGISTRE_COMMERCE},
    LegalStatus.COOPERATIVE: {DocumentType.REGISTRE_COMMERCE},
    LegalStatus.ASSOCIATION: {DocumentType.ATTESTATION},
    LegalStatus.AUTO_ENTREPRENEUR: {DocumentType.ATTESTATION},
    LegalStatus.INFORMEL: set(),
}

# Types de document susceptibles de porter le numéro d'identification légale.
DOCS_LIKELY_TO_CONTAIN_LEGAL_ID = {DocumentType.REGISTRE_COMMERCE, DocumentType.ATTESTATION}


def _normalize_for_matching(text: str) -> str:
    """Normalise pour une comparaison tolérante aux espaces/tirets/casse
    (ex: 'RC 123-456' vs 'RC123456' dans un texte OCR imparfait)."""
    return "".join(ch for ch in text.upper() if ch.isalnum())


def get_project_documents_text(db: Session, project_id: str) -> str:
    """Concatène le texte extrait (OCR) de tous les documents du dossier."""
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    return "\n---\n".join(d.extracted_text or "" for d in docs)


def check_sector_benchmark(db: Session, project_id: str) -> dict:
    """Compare le montant demandé de ce projet à ceux des autres projets
    déjà validés du même secteur — plutôt qu'à un seuil fixe, non pertinent
    d'un secteur à l'autre (un projet agricole et un projet artisanat n'ont
    pas la même échelle de montants).

    Ne compare volontairement PAS un ratio montant/emplois : deux projets
    du même secteur peuvent avoir des structures de coûts très différentes
    (un poste capitalistique — terrain, matériel lourd — coûte bien plus
    cher par emploi qu'un poste artisanal), donc un tel ratio serait aussi
    arbitraire que le seuil fixe qu'il remplace. Ce contexte de plausibilité
    est fourni au LLM sous forme de détail brut (répartition du montant par
    poste), pas via un chiffre agrégé — cf. _format_project_context."""
    project = db.get(Project, project_id)

    peers = (
        db.query(Project)
        .filter(
            Project.sector_id == project.sector_id,
            Project.status == ProjectStatus.VALIDE,
            Project.id != project.id,
        )
        .all()
    )

    if len(peers) < MIN_COMPARABLE_PROJECTS:
        return {
            "benchmark_available": False,
            "comparable_projects_count": len(peers),
            "note": (
                f"Moins de {MIN_COMPARABLE_PROJECTS} projets validés comparables "
                "dans ce secteur : pas de comparaison statistique fiable disponible."
            ),
        }

    return {
        "benchmark_available": True,
        "comparable_projects_count": len(peers),
        "project_amount_requested": float(project.amount_requested),
        "sector_median_amount_requested": median(float(p.amount_requested) for p in peers),
    }


def check_document_completeness(db: Session, project_id: str) -> dict:
    """Vérifie que les pièces attendues pour le statut juridique déclaré
    ont bien été jointes au dossier (ex: pas de registre de commerce pour
    une SARL). Le CIN est toujours attendu, quel que soit le statut."""
    project = db.get(Project, project_id)
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    present_types = {d.doc_type for d in docs}

    if project.legal_status is None:
        return {
            "legal_status": None,
            "documents_present": [t.value for t in present_types],
            "documents_missing": [DocumentType.CIN.value] if DocumentType.CIN not in present_types else [],
            "note": "Statut juridique non renseigné : seule la présence du CIN a pu être vérifiée.",
        }

    required = {DocumentType.CIN} | REQUIRED_DOCS_BY_LEGAL_STATUS.get(project.legal_status, set())
    missing = required - present_types

    return {
        "legal_status": project.legal_status.value,
        "documents_present": [t.value for t in present_types],
        "documents_missing": [t.value for t in missing],
    }


def check_legal_id_in_documents(db: Session, project_id: str) -> dict:
    """Vérifie que le numéro d'identification légale déclaré par le
    porteur (project.legal_id_number) apparaît bien dans le texte OCR
    d'un document justificatif (registre de commerce, attestation) —
    détecte un numéro déclaré mais non appuyé par une pièce jointe."""
    project = db.get(Project, project_id)

    if not project.legal_id_number:
        return {"checked": False, "note": "Aucun numéro d'identification légale déclaré pour ce projet."}

    docs = (
        db.query(Document)
        .filter(
            Document.project_id == project_id,
            Document.doc_type.in_(DOCS_LIKELY_TO_CONTAIN_LEGAL_ID),
            Document.extracted_text.isnot(None),
        )
        .all()
    )
    if not docs:
        return {
            "checked": False,
            "note": "Aucun document (registre de commerce/attestation) avec texte extrait disponible pour vérifier ce numéro.",
        }

    normalized_id = _normalize_for_matching(project.legal_id_number)
    found = any(normalized_id in _normalize_for_matching(d.extracted_text) for d in docs)

    return {
        "checked": True,
        "legal_id_number": project.legal_id_number,
        "found_in_documents": found,
        "documents_checked_count": len(docs),
    }


def check_duplicate_applications(db: Session, project_id: str) -> dict:
    """Recherche si le même porteur (ou le même CIN) a déjà soumis
    plusieurs dossiers — signal classique de fraude."""
    project = db.get(Project, project_id)
    owner = db.get(User, project.owner_id)

    other_projects_count = (
        db.query(Project)
        .filter(Project.owner_id == owner.id, Project.id != project.id)
        .count()
    )
    return {"same_owner_other_projects": other_projects_count}


# Schéma JSON envoyé à Groq pour décrire les tools disponibles
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "check_sector_benchmark",
            "description": "Compare le montant demandé de ce projet à ceux des autres projets déjà validés du même secteur",
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_duplicate_applications",
            "description": "Détecte si le porteur a d'autres dossiers en cours (risque de fraude)",
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_document_completeness",
            "description": (
                "Vérifie que les pièces attendues pour le statut juridique déclaré "
                "(registre de commerce, attestation, CIN...) ont bien été jointes au dossier"
            ),
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_legal_id_in_documents",
            "description": (
                "Vérifie que le numéro d'identification légale déclaré par le porteur "
                "apparaît bien dans le texte OCR d'une pièce jointe (registre de commerce, attestation)"
            ),
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
    },
]

TOOL_REGISTRY = {
    "check_sector_benchmark": check_sector_benchmark,
    "check_duplicate_applications": check_duplicate_applications,
    "check_document_completeness": check_document_completeness,
    "check_legal_id_in_documents": check_legal_id_in_documents,
}
