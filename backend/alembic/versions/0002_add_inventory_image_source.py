"""add source column to inventory_image

Revision ID: 0002_add_inventory_image_source
Revises: 0001_initial
Create Date: 2025-08-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_add_inventory_image_source"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inventory_image", sa.Column("source", sa.String(length=64), nullable=True))
    op.create_index("ix_inventory_image_source", "inventory_image", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inventory_image_source", table_name="inventory_image")
    op.drop_column("inventory_image", "source")
