"""Point d'import central de tous les modèles.

Importer ce module garantit que toutes les tables sont enregistrées sur
`Base.metadata` — nécessaire pour :
  - la résolution des clés étrangères (une FK vers une table non encore
    importée échoue),
  - l'autogénération des migrations Alembic,
  - `Base.metadata.create_all()` dans les tests.
"""

from app.models.ai_report import AIAnalysisReport
from app.models.chat import ChatConversation, ChatMessage
from app.models.document import Document
from app.models.investment import Investment
from app.models.knowledge import KnowledgeChunk
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_fund_usage import ProjectFundUsageItem
from app.models.refund import (
    InvestmentRefundAllocation,
    RefundInstallment,
    RefundPlan,
    RefundTier,
)
from app.models.sector import Sector
from app.models.user import User

__all__ = [
    "AIAnalysisReport",
    "ChatConversation",
    "ChatMessage",
    "Document",
    "Investment",
    "KnowledgeChunk",
    "Notification",
    "Project",
    "ProjectFundUsageItem",
    "RefundPlan",
    "RefundTier",
    "RefundInstallment",
    "InvestmentRefundAllocation",
    "Sector",
    "User",
]
