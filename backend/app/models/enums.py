import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls, name: str) -> SAEnum:
    """Construit un type ENUM SQLAlchemy qui persiste les *valeurs* de
    l'enum Python (ex: 'porteur') et non ses *noms* (ex: 'PORTEUR').

    Sans `values_callable`, SQLAlchemy utilise par défaut les noms des
    membres, ce qui ne correspond pas aux types ENUM PostgreSQL définis en
    minuscules par les migrations Alembic : toute écriture échouerait avec
    « invalid input value for enum ... ».

    À utiliser pour TOUTE colonne enum des modèles.
    """
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
    )


class UserRole(str, enum.Enum):
    PORTEUR = "porteur"
    INVESTISSEUR = "investisseur"
    ADMIN = "admin"


class ProjectStatus(str, enum.Enum):
    BROUILLON = "brouillon"
    SOUMIS = "soumis"
    EN_ANALYSE = "en_analyse"
    A_VALIDER = "a_valider"
    VALIDE = "valide"
    REJETE = "rejete"
    EN_FINANCEMENT = "en_financement"
    FINANCE = "finance"
    EN_REMBOURSEMENT = "en_remboursement"
    CLOS = "clos"
    # Échéance de collecte dépassée sans avoir atteint amount_requested (cf.
    # app/services/project_service.py::expire_funding_if_overdue).
    ECHOUE = "echoue"


class ProjectStage(str, enum.Enum):
    IDEE = "idee"
    DEMARRAGE = "demarrage"
    CROISSANCE = "croissance"


class LegalStatus(str, enum.Enum):
    AUTO_ENTREPRENEUR = "auto_entrepreneur"
    COOPERATIVE = "cooperative"
    ASSOCIATION = "association"
    SARL = "sarl"
    INFORMEL = "informel"
    AUTRE = "autre"


class RepaymentFrequency(str, enum.Enum):
    HEBDOMADAIRE = "hebdomadaire"
    MENSUELLE = "mensuelle"
    TRIMESTRIELLE = "trimestrielle"
    UNIQUE = "unique"
    A_LA_RECOLTE = "a_la_recolte"


class DocumentType(str, enum.Enum):
    CIN = "cin"
    REGISTRE_COMMERCE = "registre_commerce"
    DEVIS = "devis"
    PHOTO_PROJET = "photo_projet"
    ATTESTATION = "attestation"
    RELEVE_BANCAIRE = "releve_bancaire"
    AUTRE = "autre"


class InvestmentStatus(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    CONFIRME = "confirme"
    REMBOURSE = "rembourse"
    ANNULE = "annule"


class InstallmentStatus(str, enum.Enum):
    A_VENIR = "a_venir"
    PARTIEL = "partiel"
    LIVRE = "livre"
    EN_RETARD = "en_retard"


class AnalysisVerdict(str, enum.Enum):
    RECOMMANDE = "recommande"
    A_EXAMINER = "a_examiner"
    SUSPECT = "suspect"
    REJETE_SUGGERE = "rejete_suggere"


class ChatRole(str, enum.Enum):
    VISITEUR = "visiteur"
    PORTEUR = "porteur"
    INVESTISSEUR = "investisseur"
    ADMIN = "admin"


class MessageSender(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class KnowledgeSourceType(str, enum.Enum):
    """Origine d'un chunk indexé pour le RAG du chat."""

    PROJET = "projet"
    SECTEUR = "secteur"
    FAQ = "faq"
    # Documents de référence déposés par l'équipe (textes de loi, définitions
    # officielles...) — cf. app/data/reference_documents/.
    REFERENCE = "reference"
