"""Ajoute documents.file_hash (SHA-256 du fichier) pour la détection de
fichiers réutilisés entre dossiers/comptes par l'agent d'analyse IA.

Nullable sans backfill ici : le conteneur `migrate` ne monte pas le volume
uploads/, il ne peut donc pas lire les fichiers. Les documents existants
sont backfillés paresseusement à la première analyse qui en a besoin
(cf. app/services/agentic_analysis/tools.py::_backfill_missing_file_hashes).

Revision ID: 9a4c7d2e8f1b
Revises: e5f3a8c1b4d7
Create Date: 2026-08-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '9a4c7d2e8f1b'
down_revision: Union[str, None] = 'e5f3a8c1b4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('file_hash', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_documents_file_hash'), 'documents', ['file_hash'])


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_file_hash'), table_name='documents')
    op.drop_column('documents', 'file_hash')
