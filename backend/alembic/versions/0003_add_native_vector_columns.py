"""Add native vector columns for optimal pgvector performance

Revision ID: 0003_add_native_vector_columns
Revises: 0002_add_inventory_image_source
Create Date: 2025-08-10 12:00:00.000000

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
revision: str = '0003_add_native_vector_columns'
down_revision: Union[str, None] = '0002_add_inventory_image_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Add native vector columns to garment table
    op.add_column('garment', sa.Column('image_embedding_vec', Vector(512), nullable=True))
    op.add_column('garment', sa.Column('description_embedding_vec', Vector(1536), nullable=True))

    # Add native vector column to inventory_item table
    op.add_column('inventory_item', sa.Column('description_embedding_vec', Vector(1536), nullable=True))

    # Create HNSW indexes for optimal performance (without CONCURRENTLY for migrations)
    # Image embeddings - use L2 distance for visual similarity
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_garment_image_embedding_hnsw
        ON garment USING hnsw (image_embedding_vec vector_l2_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Description embeddings - use cosine distance for text similarity
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_garment_description_embedding_hnsw
        ON garment USING hnsw (description_embedding_vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_item_description_embedding_hnsw
        ON inventory_item USING hnsw (description_embedding_vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_inventory_item_description_embedding_hnsw')
    op.execute('DROP INDEX IF EXISTS idx_garment_description_embedding_hnsw')
    op.execute('DROP INDEX IF EXISTS idx_garment_image_embedding_hnsw')

    # Drop vector columns
    op.drop_column('inventory_item', 'description_embedding_vec')
    op.drop_column('garment', 'description_embedding_vec')
    op.drop_column('garment', 'image_embedding_vec')
