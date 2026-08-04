"""make ai_analysis_reports.verdict nullable

Revision ID: f3c9a1d2e4b7
Revises: a07d0b33b9a3
Create Date: 2026-08-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3c9a1d2e4b7'
down_revision: Union[str, None] = 'a07d0b33b9a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Permet de créer une ligne de rapport avant que l'analyse IA n'ait
    # tourné, quand l'admin tranche pendant que la tâche Celery est encore
    # en cours (cf. routers/admin.py::decide).
    op.alter_column(
        'ai_analysis_reports', 'verdict',
        existing_type=sa.Enum('recommande', 'a_examiner', 'suspect', 'rejete_suggere', name='analysis_verdict'),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'ai_analysis_reports', 'verdict',
        existing_type=sa.Enum('recommande', 'a_examiner', 'suspect', 'rejete_suggere', name='analysis_verdict'),
        nullable=False,
    )
