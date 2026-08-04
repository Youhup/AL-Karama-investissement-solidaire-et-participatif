"""add investments.share_contact_consent

Revision ID: c1a4e7f92d6b
Revises: b2f6c9d1a3e5
Create Date: 2026-08-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1a4e7f92d6b'
down_revision: Union[str, None] = 'b2f6c9d1a3e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'investments',
        sa.Column('share_contact_consent', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('investments', 'share_contact_consent', server_default=None)


def downgrade() -> None:
    op.drop_column('investments', 'share_contact_consent')
