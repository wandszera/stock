"""add receipt items and draft workflow

Revision ID: a9b8c7d6e5f4
Revises: f1a2c3d4e5f6
Create Date: 2026-04-20 23:10:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_receipt_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["receipt_id"], ["inventory_receipts.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(sa.text("UPDATE inventory_receipts SET status = 'posted' WHERE status IS NULL OR status = ''"))

    connection = op.get_bind()
    movements = connection.execute(
        sa.text(
            """
            SELECT receipt_group_id, variant_id, quantity_delta, created_at
            FROM stock_movements
            WHERE receipt_group_id IS NOT NULL
              AND movement_type = 'entry'
              AND quantity_delta > 0
            """
        )
    ).mappings()
    insert_item = sa.text(
        """
        INSERT INTO inventory_receipt_items (id, receipt_id, variant_id, quantity, created_at)
        VALUES (:id, :receipt_id, :variant_id, :quantity, :created_at)
        """
    )
    is_sqlite = connection.dialect.name == "sqlite"
    for movement in movements:
        item_id = str(uuid.uuid4()) if is_sqlite else uuid.uuid4()
        connection.execute(
            insert_item,
            {
                "id": item_id,
                "receipt_id": movement["receipt_group_id"],
                "variant_id": movement["variant_id"],
                "quantity": movement["quantity_delta"],
                "created_at": movement["created_at"],
            },
        )


def downgrade() -> None:
    op.drop_table("inventory_receipt_items")
