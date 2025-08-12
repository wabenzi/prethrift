"""Add OpenAI text embedding columns for superior text understanding

Revision ID: 0005_add_openai_text_embeddings
Revises: 0004_fix_vector_dimensions
Create Date: 2025-08-10 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector is not available
    from sqlalchemy import String as Vector


# revision identifiers, used by Alembic.
revision: str = '0005_add_openai_text_embeddings'
down_revision: Union[str, None] = '0004_fix_vector_dimensions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OpenAI text embedding columns for superior text understanding."""

    # Add OpenAI text embedding columns (1536-dimensional)
    op.add_column('garment', sa.Column('openai_text_embedding_vec', Vector(1536), nullable=True))
    op.add_column('inventory_item', sa.Column('openai_text_embedding_vec', Vector(1536), nullable=True))

    # Create HNSW indexes for OpenAI text embeddings (cosine distance)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_garment_openai_text_embedding_hnsw
        ON garment USING hnsw (openai_text_embedding_vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_item_openai_text_embedding_hnsw
        ON inventory_item USING hnsw (openai_text_embedding_vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Remove OpenAI text embedding columns."""

    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_garment_openai_text_embedding_hnsw')
    op.execute('DROP INDEX IF EXISTS idx_inventory_item_openai_text_embedding_hnsw')

    # Drop columns
    op.drop_column('garment', 'openai_text_embedding_vec')
    op.drop_column('inventory_item', 'openai_text_embedding_vec')
