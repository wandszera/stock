"""add receipt notes and audit log

Revision ID: b4c3d2e1f0a9
Revises: a9b8c7d6e5f4
Create Date: 2026-04-20 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c3d2e1f0a9"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventory_receipts", sa.Column("notes", sa.String(length=500), nullable=True))
    op.create_table(
        "inventory_receipt_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("details", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["receipt_id"], ["inventory_receipts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("inventory_receipt_audit_logs")
    op.drop_column("inventory_receipts", "notes")
