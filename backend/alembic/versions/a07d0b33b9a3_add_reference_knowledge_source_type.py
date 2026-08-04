"""add 'reference' value to knowledge_source_type enum

Revision ID: a07d0b33b9a3
Revises: d815eb945778
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a07d0b33b9a3'
down_revision: Union[str, None] = 'd815eb945778'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE ne peut pas s'exécuter dans le bloc
    # transactionnel standard d'Alembic (Postgres l'interdit avant la 12,
    # et même après il ne serait pas utilisable dans la même transaction).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE knowledge_source_type ADD VALUE IF NOT EXISTS 'reference'")


def downgrade() -> None:
    # Postgres ne permet pas de retirer une valeur d'un type ENUM.
    # Les chunks source_type='reference' devraient être supprimés
    # manuellement avant de revenir en arrière si nécessaire.
    pass
