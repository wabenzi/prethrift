"""Fix vector column dimensions to match CLIP embeddings

Revision ID: 0004_fix_vector_dimensions
Revises: 0003_add_native_vector_columns
Create Date: 2025-08-10 13:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector is not available
    from sqlalchemy import String as Vector


# revision identifiers, used by Alembic.
revision: str = "0004_fix_vector_dimensions"
down_revision: Union[str, None] = "0003_add_native_vector_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update vector columns to use 512 dimensions for CLIP compatibility."""

    # Drop existing indexes
    op.execute("DROP INDEX IF EXISTS idx_garment_description_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_inventory_item_description_embedding_hnsw")

    # Drop and recreate description vector columns with correct dimensions
    op.drop_column("garment", "description_embedding_vec")
    op.drop_column("inventory_item", "description_embedding_vec")

    # Add new columns with 512 dimensions (CLIP standard)
    op.add_column("garment", sa.Column("description_embedding_vec", Vector(512), nullable=True))
    op.add_column(
        "inventory_item", sa.Column("description_embedding_vec", Vector(512), nullable=True)
    )

    # Recreate indexes with cosine distance for both image and text (CLIP uses same space)
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
    """Revert to original vector dimensions."""

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_garment_description_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_inventory_item_description_embedding_hnsw")

    # Drop 512-dimensional columns
    op.drop_column("garment", "description_embedding_vec")
    op.drop_column("inventory_item", "description_embedding_vec")

    # Restore 1536-dimensional columns
    op.add_column("garment", sa.Column("description_embedding_vec", Vector(1536), nullable=True))
    op.add_column(
        "inventory_item", sa.Column("description_embedding_vec", Vector(1536), nullable=True)
    )

    # Recreate original indexes
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
