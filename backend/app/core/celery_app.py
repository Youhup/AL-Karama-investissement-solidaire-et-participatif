from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "solidaire_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.services.ocr_service",
        "app.services.agentic_analysis.agent",
        "app.services.knowledge_indexer",
    ],
)
