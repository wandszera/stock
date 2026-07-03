"""add supplier and document references to stock movements

Revision ID: d2b8f3c4a1e9
Revises: 9f4b8a6d2c1f
Create Date: 2026-04-20 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2b8f3c4a1e9"
down_revision: Union[str, Sequence[str], None] = "9f4b8a6d2c1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_movements", sa.Column("supplier_reference", sa.String(length=160), nullable=True))
    op.add_column("stock_movements", sa.Column("document_reference", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("stock_movements", "document_reference")
    op.drop_column("stock_movements", "supplier_reference")
