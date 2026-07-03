"""add inventory receipts header table

Revision ID: f1a2c3d4e5f6
Revises: e7c1b9a2f4d0
Create Date: 2026-04-20 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e7c1b9a2f4d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("supplier_reference", sa.String(length=160), nullable=True),
        sa.Column("document_reference", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO inventory_receipts (
                id, store_id, status, supplier_reference, document_reference, reason, created_by, received_at
            )
            SELECT
                receipt_group_id,
                store_id,
                'posted',
                supplier_reference,
                document_reference,
                reason,
                created_by,
                MIN(created_at) AS received_at
            FROM stock_movements
            WHERE receipt_group_id IS NOT NULL AND movement_type = 'entry'
            GROUP BY receipt_group_id, store_id, supplier_reference, document_reference, reason, created_by
            """
        )
    )


def downgrade() -> None:
    op.drop_table("inventory_receipts")
