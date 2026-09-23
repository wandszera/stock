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
    with op.batch_alter_table("inventory_receipts") as batch_op:
        batch_op.add_column(
            sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("approved_by", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_inventory_receipts_approved_by_users",
            "users",
            ["approved_by"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("inventory_receipts") as batch_op:
        batch_op.drop_constraint("fk_inventory_receipts_approved_by_users", type_="foreignkey")
        batch_op.drop_column("approved_by")
        batch_op.drop_column("requires_approval")
