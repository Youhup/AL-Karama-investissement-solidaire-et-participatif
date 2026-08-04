"""Génère les embeddings vectoriels utilisés pour l'indexation et la
recherche RAG du chat.

Modèle local (sentence-transformers), pas d'appel API : Groq n'expose pas
d'endpoint d'embeddings, et un modèle local évite une dépendance réseau
supplémentaire sur le chemin critique du chat. Le modèle est chargé une
seule fois (lru_cache) et réutilisé pour toutes les requêtes."""

import threading

from sentence_transformers import SentenceTransformer

from app.core.config import settings

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    # FastAPI exécute les endpoints synchrones (dont /chat) dans un
    # threadpool : deux requêtes concurrentes peuvent toutes deux tomber sur
    # un cache froid. Sans verrou, plusieurs threads instancient
    # SentenceTransformer en parallèle, ce qui fait planter le chargement
    # interne du modèle (transformers) avec "Cannot copy out of meta
    # tensor". Double-checked locking : le verrou n'est payé qu'au tout
    # premier appel.
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed(text: str) -> list[float]:
    return embed_batch([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    # normalize_embeddings=True : la similarité cosinus utilisée par
    # KnowledgeChunk.embedding.cosine_distance devient équivalente au
    # produit scalaire, ce qui est plus stable numériquement.
    vectors = model.encode(list(texts), normalize_embeddings=True)
    return vectors.tolist()
