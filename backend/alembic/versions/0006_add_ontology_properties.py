"""Add ontology-based garment properties for rich filtering and display

Revision ID: 0006_add_ontology_properties
Revises: 0005_add_openai_text_embeddings
Create Date: 2025-08-10 14:15:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_add_ontology_properties"
down_revision: Union[str, None] = "0005_add_openai_text_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ontology-based garment properties."""

    # Core garment properties from ontology
    op.add_column("garment", sa.Column("category", sa.String(64), nullable=True, index=True))
    op.add_column("garment", sa.Column("subcategory", sa.String(64), nullable=True, index=True))
    op.add_column("garment", sa.Column("primary_color", sa.String(32), nullable=True, index=True))
    op.add_column("garment", sa.Column("secondary_color", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("pattern", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("material", sa.String(64), nullable=True, index=True))
    op.add_column("garment", sa.Column("style", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("fit", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("season", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("occasion", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("era", sa.String(32), nullable=True))
    op.add_column("garment", sa.Column("gender", sa.String(16), nullable=True))

    # Size and condition
    op.add_column("garment", sa.Column("size", sa.String(16), nullable=True))
    op.add_column("garment", sa.Column("condition", sa.String(32), nullable=True))

    # Quality and value indicators
    op.add_column(
        "garment", sa.Column("designer_tier", sa.String(32), nullable=True)
    )  # luxury, premium, mid-range, etc.
    op.add_column(
        "garment", sa.Column("sustainability_score", sa.Float, nullable=True)
    )  # 0-1 score

    # Extracted confidence scores
    op.add_column(
        "garment", sa.Column("ontology_confidence", sa.Float, nullable=True)
    )  # Overall confidence in categorization
    op.add_column("garment", sa.Column("properties_extracted_at", sa.DateTime, nullable=True))

    # Create composite indexes for common filter combinations
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_garment_category_brand
        ON garment (category, brand)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_garment_category_price
        ON garment (category, price)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_garment_color_material
        ON garment (primary_color, material)
    """)


def downgrade() -> None:
    """Remove ontology properties."""

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_garment_color_material")
    op.execute("DROP INDEX IF EXISTS idx_garment_category_price")
    op.execute("DROP INDEX IF EXISTS idx_garment_category_brand")

    # Drop columns
    op.drop_column("garment", "properties_extracted_at")
    op.drop_column("garment", "ontology_confidence")
    op.drop_column("garment", "sustainability_score")
    op.drop_column("garment", "designer_tier")
    op.drop_column("garment", "condition")
    op.drop_column("garment", "size")
    op.drop_column("garment", "gender")
    op.drop_column("garment", "era")
    op.drop_column("garment", "occasion")
    op.drop_column("garment", "season")
    op.drop_column("garment", "fit")
    op.drop_column("garment", "style")
    op.drop_column("garment", "material")
    op.drop_column("garment", "pattern")
    op.drop_column("garment", "secondary_color")
    op.drop_column("garment", "primary_color")
    op.drop_column("garment", "subcategory")
    op.drop_column("garment", "category")
