"""add knowledge_chunks (RAG chat)

Revision ID: d815eb945778
Revises: 6583a892a3a1
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'd815eb945778'
down_revision: Union[str, None] = '6583a892a3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Type créé automatiquement par op.create_table ci-dessous (première
    # utilisation) — pas de création explicite pour éviter un conflit avec
    # la création implicite (DuplicateObject).
    knowledge_source_type = postgresql.ENUM(
        'projet', 'secteur', 'faq', name='knowledge_source_type'
    )

    # Réutilise le type 'chat_role' déjà créé par la migration initiale
    # (colonne chat_conversations.context_role) — create_type=False pour ne
    # pas tenter de le recréer.
    chat_role = postgresql.ENUM(
        'visiteur', 'porteur', 'investisseur', 'admin', name='chat_role', create_type=False
    )

    op.create_table(
        'knowledge_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', knowledge_source_type, nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context_role', chat_role, nullable=True),
        sa.Column('embedding', Vector(EMBEDDING_DIM), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_knowledge_chunks_source', 'knowledge_chunks', ['source_type', 'source_id']
    )
    op.create_index(
        'ix_knowledge_chunks_embedding',
        'knowledge_chunks',
        ['embedding'],
        postgresql_using='hnsw',
        postgresql_with={'m': '16', 'ef_construction': '64'},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    op.drop_index('ix_knowledge_chunks_embedding', table_name='knowledge_chunks')
    op.drop_index('ix_knowledge_chunks_source', table_name='knowledge_chunks')
    op.drop_table('knowledge_chunks')

    postgresql.ENUM(name='knowledge_source_type').drop(op.get_bind(), checkfirst=True)
