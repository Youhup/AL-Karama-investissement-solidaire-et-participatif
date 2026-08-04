"""add echoue value to project_status enum

Revision ID: e5f3a8c1b4d7
Revises: c1a4e7f92d6b
Create Date: 2026-08-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f3a8c1b4d7'
down_revision: Union[str, None] = 'c1a4e7f92d6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Représente une collecte dont l'échéance (funding_duration_days après
    # validation) est passée sans atteindre amount_requested — cf.
    # app/services/project_service.py::expire_funding_if_overdue.
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'echoue'")


def downgrade() -> None:
    # Postgres ne permet pas de retirer une valeur d'un type ENUM ;
    # downgrade non supporté pour cette migration.
    pass
