from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Plateforme Investissement Solidaire"
    ENV: str = "development"

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/solidaire_db"

    # --- Auth ---
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # --- Groq LLM ---
    # NB: llama-3.3-70b-versatile a été déprécié par Groq (annonce du 17/06/2026).
    # On utilise openai/gpt-oss-120b, la migration recommandée, qui supporte
    # bien le tool use requis par l'agent d'analyse. Vérifier la liste à jour
    # sur https://console.groq.com/docs/models avant la mise en production.
    GROQ_API_KEY: str = ""
    GROQ_CHAT_MODEL: str = "openai/gpt-oss-120b"
    GROQ_AGENT_MODEL: str = "openai/gpt-oss-120b"

    # --- Celery / Redis (pour l'analyse agentique asynchrone) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- RAG (chat) ---
    # Groq n'expose pas d'endpoint d'embeddings : modèle local, pas d'appel
    # réseau supplémentaire sur le chemin critique du chat. Multilingue
    # (le contenu à indexer est en français).
    RAG_ENABLED: bool = True
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    RAG_TOP_K: int = 5

    # --- Uploads ---
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"


settings = Settings()
