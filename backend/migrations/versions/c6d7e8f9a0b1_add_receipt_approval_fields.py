"""add receipt approval fields

Revision ID: c6d7e8f9a0b1
Revises: b4c3d2e1f0a9
Create Date: 2026-04-21 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "b4c3d2e1f0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventory_receipts", sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("inventory_receipts", sa.Column("approved_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_inventory_receipts_approved_by_users",
        "inventory_receipts",
        "users",
        ["approved_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_inventory_receipts_approved_by_users", "inventory_receipts", type_="foreignkey")
    op.drop_column("inventory_receipts", "approved_by")
    op.drop_column("inventory_receipts", "requires_approval")
