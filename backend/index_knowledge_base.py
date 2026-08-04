"""Réindexe la base de connaissances du chat (RAG) sans toucher au reste
des données : projets publics, secteurs, FAQ.

À lancer après un déploiement sur une base existante (ex: activation du
RAG sur une instance qui tournait déjà), ou pour rafraîchir manuellement
l'index après une modification du contenu FAQ (app/data/faq_content.py).

Usage (depuis backend/) :

    python index_knowledge_base.py
"""
import sys

sys.path.insert(0, ".")

from app.db.session import SessionLocal
from app.models import Project, Sector  # noqa: F401  (enregistre les tables)
from app.services.knowledge_indexer import reindex_all


def main():
    db = SessionLocal()
    try:
        reindex_all(db)
        print("Base de connaissances RAG réindexée.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
